package gov.nih.nci.evs.operations.admin;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;

/** Private control plane. Backend clients are initialized only by loader child JVMs. */
@SpringBootApplication
@EnableConfigurationProperties(AdminProperties.class)
public class AdminApplication {
  public static void main(String[] args) {
    SpringApplication.run(AdminApplication.class, args);
  }
}
