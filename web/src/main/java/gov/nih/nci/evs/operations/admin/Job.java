package gov.nih.nci.evs.operations.admin;

import java.time.Instant;
import java.util.List;

/** Persisted API process record. PID is diagnostic; id is the public identifier. */
public class Job {
  private String id;
  private String command;
  private List<String> args;
  private String state;
  private Instant submittedAt;
  private Instant startedAt;
  private Instant finishedAt;
  private Integer exitCode;
  private Long pid;
  private Instant processStartedAt;
  private String output;
  private boolean outputTruncated;

  public String getId() {
    return id;
  }

  public void setId(String value) {
    id = value;
  }

  public String getCommand() {
    return command;
  }

  public void setCommand(String value) {
    command = value;
  }

  public List<String> getArgs() {
    return args;
  }

  public void setArgs(List<String> value) {
    args = value == null ? null : List.copyOf(value);
  }

  public String getState() {
    return state;
  }

  public void setState(String value) {
    state = value;
  }

  public Instant getSubmittedAt() {
    return submittedAt;
  }

  public void setSubmittedAt(Instant value) {
    submittedAt = value;
  }

  public Instant getStartedAt() {
    return startedAt;
  }

  public void setStartedAt(Instant value) {
    startedAt = value;
  }

  public Instant getFinishedAt() {
    return finishedAt;
  }

  public void setFinishedAt(Instant value) {
    finishedAt = value;
  }

  public Integer getExitCode() {
    return exitCode;
  }

  public void setExitCode(Integer value) {
    exitCode = value;
  }

  public Long getPid() {
    return pid;
  }

  public void setPid(Long value) {
    pid = value;
  }

  public Instant getProcessStartedAt() {
    return processStartedAt;
  }

  public void setProcessStartedAt(Instant value) {
    processStartedAt = value;
  }

  public String getOutput() {
    return output;
  }

  public void setOutput(String value) {
    output = value;
  }

  public boolean isOutputTruncated() {
    return outputTruncated;
  }

  public void setOutputTruncated(boolean value) {
    outputTruncated = value;
  }
}
