package gov.nih.nci.evs.operations.admin;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PreDestroy;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/** Disk-backed API jobs. Scripts remain the only implementation of operational workflows. */
@Service
public final class JobService {
  public static final int MAX_OUTPUT = 1024 * 1024;
  public static final int MIN_KEY_LENGTH = 32;
  // Environment variables whose values are masked in job arguments and output.
  private static final String SECRET_NAMES =
      "(?i).*(PASSW|PASSPHRASE|SECRET|TOKEN|CREDENTIAL|ADMIN_KEY|API_KEY).*";
  private final AdminProperties properties;
  private final CommandRegistry registry;
  private final ObjectMapper mapper = new ObjectMapper().findAndRegisterModules();
  private final Map<String, Job> jobs = new ConcurrentHashMap<>();
  private final Map<String, Process> processes = new ConcurrentHashMap<>();
  private final Map<String, CompletableFuture<Void>> completions = new ConcurrentHashMap<>();
  private final ExecutorService executor = Executors.newVirtualThreadPerTaskExecutor();
  private final List<String> secrets;
  private final Object lifecycle = new Object();
  private volatile boolean closing;

  public record LogChunk(long offset, long nextOffset, boolean complete, String output) {}

  public JobService(AdminProperties properties, CommandRegistry registry) throws IOException {
    this.properties = properties;
    this.registry = registry;
    if (properties.getApiKey() == null
        || properties.getApiKey().isBlank()
        || properties.getApiKey().length() < MIN_KEY_LENGTH)
      throw new IllegalArgumentException(
          "ADMIN_KEY must be configured with at least " + MIN_KEY_LENGTH + " characters");
    secrets = new ArrayList<>();
    secrets.add(properties.getApiKey());
    System.getenv()
        .forEach(
            (key, value) -> {
              if (key.matches(SECRET_NAMES) && !value.isEmpty()) secrets.add(value);
            });
    // Longest first, so a secret that contains another is never partly revealed.
    secrets.sort(Comparator.comparingInt(String::length).reversed());
    if (properties.getWaitSeconds() < 0 || properties.getRetentionDays() < 1)
      throw new IllegalArgumentException("Invalid process retention or wait settings");
    Files.createDirectories(properties.getStateDir().resolve("jobs"));
    try (var directories = Files.list(properties.getStateDir().resolve("jobs"))) {
      for (Path directory : directories.filter(Files::isDirectory).toList()) {
        if (!directory.toFile().getName().matches("[a-f0-9-]{36}")) continue;
        Path metadata = directory.resolve("job.json");
        if (!Files.exists(metadata)) continue;
        Job job = mapper.readValue(metadata.toFile(), Job.class);
        if (!directory.toFile().getName().equals(job.getId()))
          throw new IOException("Process metadata does not match its directory");
        if (!terminal(job)) {
          job.setState("INTERRUPTED");
          job.setFinishedAt(Instant.now());
          persist(job);
        }
        jobs.put(job.getId(), job);
      }
    }
    cleanup();
  }

  private Path directory(String id) {
    UUID.fromString(id);
    return properties.getStateDir().resolve("jobs").resolve(id);
  }

  private boolean terminal(Job job) {
    return List.of("SUCCEEDED", "FAILED", "INTERRUPTED").contains(job.getState());
  }

  private void persist(Job job) throws IOException {
    Path destination = directory(job.getId()).resolve("job.json");
    Path temporary = destination.resolveSibling("job.json.tmp");
    mapper.writeValue(temporary.toFile(), job);
    try {
      Files.move(
          temporary,
          destination,
          StandardCopyOption.REPLACE_EXISTING,
          StandardCopyOption.ATOMIC_MOVE);
    } catch (AtomicMoveNotSupportedException e) {
      Files.move(temporary, destination, StandardCopyOption.REPLACE_EXISTING);
    }
  }

  private boolean orphanRunning() {
    return jobs.values().stream()
        .filter(j -> "INTERRUPTED".equals(j.getState()) && j.getPid() != null)
        .anyMatch(
            j ->
                ProcessHandle.of(j.getPid())
                    .filter(ProcessHandle::isAlive)
                    .filter(
                        p ->
                            j.getProcessStartedAt() == null
                                || p.info()
                                    .startInstant()
                                    .map(j.getProcessStartedAt()::equals)
                                    .orElse(true))
                    .isPresent());
  }

  public Job submit(String name, List<String> arguments) throws IOException, InterruptedException {
    if (closing) throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE);
    CommandRegistry.Command command = registry.get(name);
    List<String> args = arguments == null ? List.of() : List.copyOf(arguments);
    if (args.size() > 100
        || args.stream().anyMatch(a -> a == null || a.indexOf('\0') >= 0 || a.length() > 32768))
      throw new IllegalArgumentException("Invalid command arguments");
    if (command.mutation() && orphanRunning())
      throw new ResponseStatusException(HttpStatus.CONFLICT, "An interrupted worker still exists");
    Path script = properties.getHome().resolve("bin").resolve(command.script());
    if (!Files.isRegularFile(script)) throw new IOException("Registered script is unavailable");
    cleanup();
    Job job = new Job();
    job.setId(UUID.randomUUID().toString());
    job.setCommand(name);
    job.setArgs(args.stream().map(this::redact).toList());
    job.setState("STARTING");
    job.setSubmittedAt(Instant.now());
    Files.createDirectory(directory(job.getId()));
    persist(job);
    jobs.put(job.getId(), job);
    Path ready = directory(job.getId()).resolve("ready.json");
    List<String> invocation =
        new ArrayList<>(
            List.of(
                properties.getPython(),
                properties.getHome().resolve("bin/process_supervisor.py").toString(),
                "--ready-file",
                ready.toString()));
    if (!command.mutation()) invocation.add("--read-only");
    invocation.add("--command-env");
    List<String> commandArguments =
        new ArrayList<>(List.of(properties.getBash(), script.toString()));
    commandArguments.addAll(args);
    ProcessBuilder builder =
        new ProcessBuilder(invocation)
            .directory(properties.getHome().toFile())
            .redirectErrorStream(true);
    builder.environment().put("EVS_OPS_HOME", properties.getHome().toString());
    builder.environment().put("OPS_STATE_DIR", properties.getStateDir().toString());
    builder.environment().put("OPS_PYTHON", properties.getPython());
    builder.environment().put("OPS_BASH", properties.getBash());
    builder.environment().put("PYTHONUTF8", "1");
    // Keep literal quotes intact across native Windows Java/Python/Bash argv parsers.
    builder.environment().put("EVS_OPS_COMMAND_ARGC", Integer.toString(commandArguments.size()));
    for (int i = 0; i < commandArguments.size(); i++) {
      builder.environment().put("EVS_OPS_COMMAND_ARG_" + i, commandArguments.get(i));
    }
    // API callers cannot inherit a stale lock bypass context from service startup.
    builder.environment().remove("EVS_OPS_LOCK_TOKEN");
    // Scripts and the tools they run never need the API key.
    builder.environment().remove("ADMIN_KEY");
    Process process;
    CompletableFuture<Void> completed = new CompletableFuture<>();
    synchronized (lifecycle) {
      if (closing) throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE);
      try {
        process = builder.start();
        process.getOutputStream().close();
      } catch (IOException e) {
        job.setState("FAILED");
        job.setFinishedAt(Instant.now());
        persist(job);
        throw e;
      }
      job.setPid(process.pid());
      job.setStartedAt(Instant.now());
      job.setProcessStartedAt(process.info().startInstant().orElse(null));
      persist(job);
      processes.put(job.getId(), process);
      completions.put(job.getId(), completed);
      executor.submit(() -> run(job, process, completed));
    }
    long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(10);
    while (!Files.exists(ready) && process.isAlive() && System.nanoTime() < deadline)
      Thread.sleep(20);
    if (Files.exists(ready)) {
      String state = mapper.readTree(ready.toFile()).path("state").asText();
      if ("BUSY".equals(state)) {
        throw new ResponseStatusException(
            HttpStatus.CONFLICT, "Another data-changing operation is running");
      }
      synchronized (job) {
        if (!terminal(job)) {
          job.setState("RUNNING");
          persist(job);
        }
      }
    } else if (process.isAlive()) {
      process.destroy();
      throw new IOException("Process supervisor did not acknowledge startup");
    }
    return get(job.getId());
  }

  private String redact(String text) {
    String result = text;
    for (String secret : secrets) result = result.replace(secret, "****");
    return result
        .replaceAll("(?i)(apiKey|password|token|secret)=([^\\s&]+)", "$1=****")
        .replaceAll("(://[^/\\s:@]+:)[^/\\s@]+@", "$1****@");
  }

  private void run(Job job, Process process, CompletableFuture<Void> completed) {
    try (var input =
            new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
        var output =
            Files.newBufferedWriter(
                directory(job.getId()).resolve("process.log"), StandardCharsets.UTF_8)) {
      // Drain throughout execution; never wait for exit with unread stderr/stdout pipes.
      char[] buffer = new char[4096];
      StringBuilder pending = new StringBuilder();
      int keep = secrets.stream().mapToInt(String::length).max().orElse(1);
      boolean multilineSecret = secrets.stream().anyMatch(s -> s.indexOf('\n') >= 0);
      int count;
      while ((count = input.read(buffer)) != -1) {
        pending.append(buffer, 0, count);
        int cut = Math.max(0, pending.length() - keep);
        if (!multilineSecret) cut = Math.max(cut, pending.lastIndexOf("\n") + 1);
        for (String secret : secrets) {
          int start = pending.lastIndexOf(secret, cut - 1);
          if (start >= 0 && start + secret.length() > cut) cut = start;
        }
        output.write(redact(pending.substring(0, cut)));
        pending.delete(0, cut);
        output.flush();
      }
      output.write(redact(pending.toString()));
      output.flush();
      int exit = process.waitFor();
      synchronized (job) {
        job.setExitCode(exit);
        job.setState(closing || exit == 130 ? "INTERRUPTED" : exit == 0 ? "SUCCEEDED" : "FAILED");
        job.setFinishedAt(Instant.now());
        persist(job);
      }
      completed.complete(null);
    } catch (Exception e) {
      process.destroy();
      synchronized (job) {
        job.setState("FAILED");
        job.setFinishedAt(Instant.now());
        try {
          persist(job);
        } catch (IOException failure) {
          completed.completeExceptionally(failure);
        }
      }
      completed.completeExceptionally(e);
    } finally {
      processes.remove(job.getId());
    }
  }

  public Job await(String id) throws Exception {
    CompletableFuture<Void> completion = completions.get(id);
    if (completion != null) {
      try {
        completion.get(properties.getWaitSeconds(), TimeUnit.SECONDS);
      } catch (java.util.concurrent.TimeoutException e) {
        /* Continue through polling. */
      } catch (java.util.concurrent.ExecutionException e) {
        /* Output capture failed; the job record already says FAILED. */
      }
    }
    Job job = get(id);
    if (terminal(job)) {
      LogChunk log = log(id, 0, MAX_OUTPUT);
      job.setOutput(log.output());
      job.setOutputTruncated(!log.complete());
    }
    return job;
  }

  public Job get(String id) {
    if (id == null || !id.matches("[a-f0-9-]{36}"))
      throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    Job job = jobs.get(id);
    if (job == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND);
    synchronized (job) {
      return mapper.convertValue(job, Job.class);
    }
  }

  public List<Job> list(int page, int size) {
    if (page < 0 || size < 1 || size > 100)
      throw new IllegalArgumentException("Invalid pagination");
    return jobs.values().stream()
        .sorted(Comparator.comparing((Job j) -> j.getSubmittedAt()).reversed())
        .skip((long) page * size)
        .limit(size)
        .map(j -> get(j.getId()))
        .toList();
  }

  public Path logPath(String id) {
    get(id);
    return directory(id).resolve("process.log");
  }

  public LogChunk log(String id, long offset, int limit) throws IOException {
    Job job = get(id);
    if (offset < 0 || limit < 1 || limit > MAX_OUTPUT)
      throw new IllegalArgumentException("Invalid log range");
    Path path = logPath(id);
    if (!Files.exists(path)) return new LogChunk(offset, offset, terminal(job), "");
    try (RandomAccessFile file = new RandomAccessFile(path.toFile(), "r")) {
      if (offset > file.length()) throw new IllegalArgumentException("Offset is beyond the log");
      file.seek(offset);
      byte[] bytes = new byte[(int) Math.min(limit, file.length() - offset)];
      file.readFully(bytes);
      int count = bytes.length;
      // Preserve a split UTF-8 character for the next poll.
      if (offset + count < file.length()) {
        int lead = count - 1;
        while (lead >= 0 && (bytes[lead] & 0xc0) == 0x80) lead--;
        if (lead >= 0) {
          int expected =
              (bytes[lead] & 0xf8) == 0xf0
                  ? 4
                  : (bytes[lead] & 0xf0) == 0xe0 ? 3 : (bytes[lead] & 0xe0) == 0xc0 ? 2 : 1;
          if (count - lead < expected) count = lead;
        }
      }
      return new LogChunk(
          offset,
          offset + count,
          terminal(job) && offset + count == file.length(),
          new String(bytes, 0, count, StandardCharsets.UTF_8));
    }
  }

  private synchronized void cleanup() throws IOException {
    Instant cutoff = Instant.now().minus(properties.getRetentionDays(), ChronoUnit.DAYS);
    for (Job job : List.copyOf(jobs.values())) {
      if (terminal(job)
          && job.getFinishedAt() != null
          && job.getFinishedAt().isBefore(cutoff)
          && !processes.containsKey(job.getId())) {
        if (job.getPid() != null
            && ProcessHandle.of(job.getPid()).filter(ProcessHandle::isAlive).isPresent()) continue;
        try (var files = Files.list(directory(job.getId()))) {
          for (Path file : files.toList()) Files.delete(file);
        }
        Files.delete(directory(job.getId()));
        jobs.remove(job.getId());
        completions.remove(job.getId());
      }
    }
  }

  @PreDestroy
  public void stop() throws InterruptedException {
    synchronized (lifecycle) {
      closing = true;
      for (Process process : processes.values()) process.destroy();
      executor.shutdown();
    }
    if (!executor.awaitTermination(20, TimeUnit.SECONDS)) {
      for (Process process : processes.values()) {
        process.descendants().forEach(ProcessHandle::destroyForcibly);
        process.destroyForcibly();
      }
      executor.shutdownNow();
    }
  }
}
