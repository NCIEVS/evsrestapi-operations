package gov.nih.nci.evs.operations.admin;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.springframework.stereotype.Component;

/** Fixed active workflow registry; arguments are passed without shell evaluation. */
@Component
public class CommandRegistry {
  public record Command(String name, String script, boolean mutation, String usage) {}

  private final Map<String, Command> commands =
      List.of(
              new Command(
                  "load",
                  "stardog_load.sh",
                  true,
                  "[--noconfig] [--force] [--weekly] <file-or-url>"),
              new Command("bulk-load", "bulk_load.sh", true, "[--noconfig] [--force]"),
              new Command(
                  "reindex",
                  "reindex.sh",
                  true,
                  "[--noconfig] [--history file] [--terminology name]"),
              new Command("ncim", "ncim.sh", true, "[--download]"),
              new Command(
                  "ncim-part",
                  "ncim-part.sh",
                  true,
                  "[--noconfig] [--download] [--keep] [--terminology name] [RRF-directory]"),
              new Command(
                  "devreset", "devreset.sh", true, "[--test-reconcile] <UnitTestData-directory>"),
              new Command("load-local", "load.sh", true, "<UnitTestData-directory>"),
              new Command(
                  "report",
                  "report.sh",
                  false,
                  "[--noconfig] [--list] [<database> <terminology> <version>]"),
              new Command("list", "list.sh", false, "[--noconfig] [--quiet] [--graphdb] [--es]"),
              new Command(
                  "remove",
                  "remove.sh",
                  true,
                  "[--noconfig] <terminology> <version> --graphdb|--es; or --mapset <code>"),
              new Command(
                  "metadata", "metadata.sh", true, "[--noconfig] <terminology> <version> <config>"),
              new Command("init", "init.sh", true, "[--noconfig] [--quiet]"),
              new Command(
                  "audit",
                  "audit.sh",
                  false,
                  "[--noconfig] [--csv|--tsv] [--recent] <load|stats|error|warning|all>"
                      + " [terminology]"),
              new Command(
                  "command",
                  "run_command.sh",
                  true,
                  "[--noconfig]"
                      + " print_env|list|remove|patch|metadata|init|audit|drop_ctrp_db|list_compaction_tasks"
                      + " ..."),
              new Command(
                  "qa",
                  "stardog_qa.sh",
                  false,
                  "<terminology> <OWL-file> <weekly-flag> <input-directory>"),
              new Command(
                  "owl-sampling",
                  "owl_sampling.sh",
                  false,
                  "<OWL-file> <terminology-JSON> [--output file] [--terminology name] [--report"
                      + " file]"),
              new Command(
                  "rrf-sampling",
                  "rrf_sampling.sh",
                  false,
                  "<RRF-directory> <config-directory> <terminology>"),
              new Command(
                  "java-rrf-sampling",
                  "java_rrf_sampling.sh",
                  false,
                  "<inputPath> <list-file> <terminologies> [codesab|cui]"),
              new Command(
                  "load-testing",
                  "load_testing.sh",
                  false,
                  "[--url url] [--time ms] [--calls count]"),
              new Command("cdisc-form-update", "cdisc_form_update.sh", true, "<codes-file>"),
              new Command(
                  "transform-hgnc",
                  "transforms/hgnc.sh",
                  true,
                  "<input-file> <process-id> [ontology-URL]"),
              new Command(
                  "transform-canmed",
                  "transforms/canmed.sh",
                  true,
                  "<input-file> <process-id> [ontology-URL]"),
              new Command(
                  "transform-medrt",
                  "transforms/medrt.sh",
                  true,
                  "<input-file> <process-id> [ontology-URL]"),
              new Command(
                  "transform-umlssemnet",
                  "transforms/umlssemnet.sh",
                  true,
                  "<input-file> <process-id> [version] [ontology-URL]"))
          .stream()
          .collect(Collectors.toUnmodifiableMap(Command::name, Function.identity()));

  public List<Command> list() {
    return commands.values().stream()
        .sorted(java.util.Comparator.comparing(Command::name))
        .toList();
  }

  public Command get(String name) {
    Command command = name == null ? null : commands.get(name);
    if (command == null) throw new IllegalArgumentException("Unknown operation");
    return command;
  }
}
