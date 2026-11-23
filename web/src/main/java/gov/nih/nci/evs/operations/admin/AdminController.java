package gov.nih.nci.evs.operations.admin;

import java.io.IOException;
import java.nio.file.Files;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.mvc.method.annotation.StreamingResponseBody;

/** Private API for script-backed operations. */
@RestController
@RequestMapping("/admin")
public class AdminController {
  private static final org.slf4j.Logger logger =
      org.slf4j.LoggerFactory.getLogger(AdminController.class);
  private final JobService jobs;
  private final CommandRegistry registry;

  public record ExecuteRequest(String command, List<String> args) {
    public ExecuteRequest {
      args = args == null ? List.of() : List.copyOf(args);
    }
  }

  public AdminController(JobService jobs, CommandRegistry registry) {
    this.jobs = jobs;
    this.registry = registry;
  }

  @GetMapping("/commands")
  public List<CommandRegistry.Command> commands() {
    return registry.list();
  }

  @PostMapping("/exec")
  public ResponseEntity<Job> exec(
      @RequestBody ExecuteRequest request, @RequestParam(defaultValue = "false") boolean background)
      throws Exception {
    Job job = jobs.submit(request.command(), request.args());
    if (!background) job = jobs.await(job.getId());
    boolean done = List.of("SUCCEEDED", "FAILED", "INTERRUPTED").contains(job.getState());
    return ResponseEntity.status(done ? 200 : 202)
        .header("Location", "/admin/processes/" + job.getId())
        .body(job);
  }

  @GetMapping("/processes")
  public List<Job> processes(
      @RequestParam(defaultValue = "0") int page, @RequestParam(defaultValue = "20") int size) {
    return jobs.list(page, size);
  }

  @GetMapping("/processes/{id}")
  public Job process(@PathVariable String id) {
    return jobs.get(id);
  }

  @GetMapping("/processes/{id}/log")
  public ResponseEntity<StreamingResponseBody> log(
      @PathVariable String id,
      @RequestParam(defaultValue = "0") long offset,
      @RequestParam(defaultValue = "1048576") int limit,
      @RequestParam(defaultValue = "false") boolean full)
      throws IOException {
    if (!full) {
      var chunk = jobs.log(id, offset, limit);
      StreamingResponseBody body =
          output -> new com.fasterxml.jackson.databind.ObjectMapper().writeValue(output, chunk);
      return ResponseEntity.ok().header("Content-Type", "application/json").body(body);
    }
    var path = jobs.logPath(id);
    StreamingResponseBody body =
        output -> {
          if (Files.exists(path)) Files.copy(path, output);
        };
    return ResponseEntity.ok().header("Content-Type", "text/plain;charset=UTF-8").body(body);
  }

  @ExceptionHandler(IllegalArgumentException.class)
  @ResponseStatus(HttpStatus.BAD_REQUEST)
  public Map<String, String> invalid() {
    return Map.of("error", "Invalid operation, arguments, or range");
  }

  @ExceptionHandler(IOException.class)
  @ResponseStatus(HttpStatus.INTERNAL_SERVER_ERROR)
  public Map<String, String> failed(IOException error) {
    logger.error("Process storage or launch failed", error);
    return Map.of("error", "Process storage or launch failed; inspect service diagnostics");
  }
}
