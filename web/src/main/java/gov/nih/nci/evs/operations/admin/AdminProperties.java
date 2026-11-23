package gov.nih.nci.evs.operations.admin;

import java.nio.file.Path;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Configuration for the private operations service. */
@ConfigurationProperties("admin")
public class AdminProperties {
  private String apiKey;
  private Path home = Path.of("..").toAbsolutePath().normalize();
  private Path stateDir;
  private String python = "python3";
  private String bash = "bash";
  private int waitSeconds = 300;
  private int retentionDays = 30;

  public String getApiKey() {
    return apiKey;
  }

  public void setApiKey(String value) {
    apiKey = value;
  }

  public Path getHome() {
    return home;
  }

  public void setHome(Path value) {
    home = value.toAbsolutePath().normalize();
  }

  public Path getStateDir() {
    return stateDir == null ? home.resolve("var") : stateDir;
  }

  public void setStateDir(Path value) {
    stateDir = value.toAbsolutePath().normalize();
  }

  public String getPython() {
    return python;
  }

  public void setPython(String value) {
    python = value;
  }

  public String getBash() {
    return bash;
  }

  public void setBash(String value) {
    bash = value;
  }

  public int getWaitSeconds() {
    return waitSeconds;
  }

  public void setWaitSeconds(int value) {
    waitSeconds = value;
  }

  public int getRetentionDays() {
    return retentionDays;
  }

  public void setRetentionDays(int value) {
    retentionDays = value;
  }
}
