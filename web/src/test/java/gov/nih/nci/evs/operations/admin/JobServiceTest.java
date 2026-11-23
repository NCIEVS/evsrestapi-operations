package gov.nih.nci.evs.operations.admin;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.web.server.ResponseStatusException;

/** Exercises actual supervisor/script processes without graph or OpenSearch. */
class JobServiceTest {
  private static final String KEY = "test-private-key-0123456789abcdef";
  @TempDir Path directory;
  private JobService service;
  private int waitSeconds = 10;

  private AdminProperties properties() {
    AdminProperties p = new AdminProperties();
    p.setApiKey(KEY);
    p.setHome(directory);
    p.setPython(System.getProperty("os.name").startsWith("Windows") ? "python" : "python3");
    p.setBash(
        System.getProperty("os.name").startsWith("Windows")
            ? "C:/Program Files/Git/bin/bash.exe"
            : "bash");
    p.setWaitSeconds(waitSeconds);
    return p;
  }

  private void start(String content) throws Exception {
    Files.createDirectories(directory.resolve("bin"));
    Files.copy(
        Path.of("../bin/process_supervisor.py"), directory.resolve("bin/process_supervisor.py"));
    Files.copy(Path.of("../bin/process_exec.sh"), directory.resolve("bin/process_exec.sh"));
    Files.writeString(directory.resolve("bin/fixture.sh"), content);
    CommandRegistry registry = mock(CommandRegistry.class);
    when(registry.get("fixture"))
        .thenReturn(new CommandRegistry.Command("fixture", "fixture.sh", true, ""));
    service = new JobService(properties(), registry);
  }

  @AfterEach
  void stop() throws Exception {
    if (service != null) service.stop();
  }

  @Test
  void preservesQuotesEmptyArgumentsAndUnicode() throws Exception {
    start("#!/bin/bash\nprintf '%s\\0' \"$@\"\n");
    List<String> arguments =
        List.of(
            "space value", "single'quote", "double\"quote", "$(literal)", "semi;colon", "", "é漢🚀");
    Job job = service.await(service.submit("fixture", arguments).getId());
    assertEquals("SUCCEEDED", job.getState());
    assertEquals(String.join("\0", arguments) + "\0", job.getOutput());
  }

  @Test
  void capturesBothStreamsAndLiteralArguments() throws Exception {
    start("#!/bin/bash\nprintf '%s\\n' \"$1\"\necho stderr >&2\necho " + KEY + "\n");
    String literal = "spaces $(do-not-execute) ; & quote'";
    Job job = service.submit("fixture", List.of(literal));
    job = service.await(job.getId());
    assertEquals("SUCCEEDED", job.getState());
    assertTrue(job.getOutput().contains(literal));
    assertTrue(job.getOutput().contains("stderr"));
    assertFalse(job.getOutput().contains(KEY));
    assertEquals(0, job.getExitCode());
  }

  @Test
  void preservesFailureAndHistoryAfterRestart() throws Exception {
    start("#!/bin/bash\necho failure >&2\nexit 7\n");
    Job job = service.submit("fixture", List.of());
    job = service.await(job.getId());
    assertEquals("FAILED", job.getState());
    assertEquals(7, job.getExitCode());
    service.stop();
    service = new JobService(properties(), mock(CommandRegistry.class));
    assertEquals("FAILED", service.get(job.getId()).getState());
    assertTrue(service.log(job.getId(), 0, 100).output().contains("failure"));
  }

  @Test
  void rejectsConcurrentMutationAndTimesOutToPolling() throws Exception {
    waitSeconds = 0;
    start("#!/bin/bash\necho started\nsleep 3\necho finished\n");
    Job first = service.submit("fixture", List.of());
    long progressDeadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(1);
    while (!service.log(first.getId(), 0, 100).output().contains("started")
        && System.nanoTime() < progressDeadline) Thread.sleep(20);
    assertTrue(service.log(first.getId(), 0, 100).output().contains("started"));
    ResponseStatusException failure =
        assertThrows(ResponseStatusException.class, () -> service.submit("fixture", List.of()));
    assertEquals(409, failure.getStatusCode().value());
    Job result = service.await(first.getId());
    assertEquals("RUNNING", result.getState());
    long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(5);
    while (!List.of("SUCCEEDED", "FAILED").contains(result.getState())
        && System.nanoTime() < deadline) {
      Thread.sleep(30);
      result = service.get(first.getId());
    }
    assertEquals("SUCCEEDED", result.getState());
  }

  @Test
  void preservesLogsWithoutNewlinesAndMasksSplitSecrets() throws Exception {
    start(
        "#!/bin/bash\n"
            + "printf 'prefix-test-'; sleep 0.1; printf 'private-key-0123456789abcdef-suffix'\n");
    Job job = service.await(service.submit("fixture", List.of()).getId());
    assertEquals("prefix-****-suffix", job.getOutput());
  }

  @Test
  void marksUnfinishedHistoryInterruptedAndExpiresCompletedHistory() throws Exception {
    var props = properties();
    Path jobDir = props.getStateDir().resolve("jobs/00000000-0000-0000-0000-000000000001");
    Files.createDirectories(jobDir);
    Job unfinished = new Job();
    unfinished.setId(jobDir.toFile().getName());
    unfinished.setCommand("fixture");
    unfinished.setState("STARTING");
    unfinished.setSubmittedAt(java.time.Instant.now());
    new com.fasterxml.jackson.databind.ObjectMapper()
        .findAndRegisterModules()
        .writeValue(jobDir.resolve("job.json").toFile(), unfinished);
    service = new JobService(props, new CommandRegistry());
    assertEquals("INTERRUPTED", service.get(unfinished.getId()).getState());
    assertNotNull(service.get(unfinished.getId()).getFinishedAt());
    service.stop();
    unfinished.setState("SUCCEEDED");
    unfinished.setFinishedAt(java.time.Instant.now().minus(31, java.time.temporal.ChronoUnit.DAYS));
    new com.fasterxml.jackson.databind.ObjectMapper()
        .findAndRegisterModules()
        .writeValue(jobDir.resolve("job.json").toFile(), unfinished);
    service = new JobService(props, new CommandRegistry());
    assertTrue(service.list(0, 20).isEmpty());
    assertFalse(Files.exists(jobDir));
  }

  @Test
  void boundsOutputAndSupportsIncrementalLogs() throws Exception {
    start("#!/bin/bash\nfor ((i=0;i<18000;i++)); do printf '%0100d\\n' 0; done\n");
    Job job = service.submit("fixture", List.of());
    job = service.await(job.getId());
    assertEquals("SUCCEEDED", job.getState());
    assertTrue(job.isOutputTruncated());
    assertTrue(job.getOutput().length() <= JobService.MAX_OUTPUT);
    var first = service.log(job.getId(), 0, 512);
    var next = service.log(job.getId(), first.nextOffset(), 512);
    assertEquals(1024, next.nextOffset());
    String id = job.getId();
    assertThrows(IllegalArgumentException.class, () -> service.log(id, -1, 100));
  }

  @Test
  void returnsTheJobWhenOutputCaptureFails() throws Exception {
    start("#!/bin/bash\necho partial\n");
    Job job = service.await(service.submit("fixture", List.of()).getId());
    // Stand in for a failed output drain, such as a full disk while writing process.log.
    @SuppressWarnings("unchecked")
    var completions =
        (java.util.Map<String, java.util.concurrent.CompletableFuture<Void>>)
            java.util.Objects.requireNonNull(
                org.springframework.test.util.ReflectionTestUtils.getField(service, "completions"));
    completions.put(
        job.getId(),
        java.util.concurrent.CompletableFuture.failedFuture(new java.io.IOException("disk full")));
    Job result = service.await(job.getId());
    assertEquals(job.getId(), result.getId());
    assertTrue(result.getOutput().contains("partial"));
  }

  @Test
  void masksCredentialsInUrls() throws Exception {
    start("#!/bin/bash\necho \"$1\" http://localhost:3030/b\n");
    String url = "https://user:hunter2@example.org/a";
    Job job = service.await(service.submit("fixture", List.of(url)).getId());
    assertEquals(List.of("https://user:****@example.org/a"), job.getArgs());
    assertTrue(job.getOutput().contains("https://user:****@example.org/a http://localhost:3030/b"));
    assertFalse(job.getOutput().contains("hunter2"));
  }

  @Test
  void rejectsMissingOrShortKey() {
    AdminProperties p = properties();
    p.setApiKey(" ");
    assertThrows(IllegalArgumentException.class, () -> new JobService(p, new CommandRegistry()));
    p.setApiKey("x".repeat(JobService.MIN_KEY_LENGTH - 1));
    assertThrows(IllegalArgumentException.class, () -> new JobService(p, new CommandRegistry()));
  }
}
