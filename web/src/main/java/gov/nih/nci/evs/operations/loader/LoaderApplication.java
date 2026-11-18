package gov.nih.nci.evs.operations.loader;

import gov.nih.nci.evs.api.configuration.OpensearchConfiguration;
import gov.nih.nci.evs.api.properties.ApplicationProperties;
import gov.nih.nci.evs.api.properties.GraphProperties;
import gov.nih.nci.evs.api.properties.OpensearchQueryProperties;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;

/** Non-web context containing only terminology data services and loaders. */
@SpringBootApplication(
    scanBasePackages = {"gov.nih.nci.evs.api.service", "gov.nih.nci.evs.api.util"})
@Import(OpensearchConfiguration.class)
@EnableCaching
public class LoaderApplication {
  @Bean
  @ConfigurationProperties("nci.evs.application")
  ApplicationProperties applicationProperties() {
    return new ApplicationProperties();
  }

  @Bean
  @ConfigurationProperties("nci.evs.graph")
  GraphProperties graphProperties() {
    return new GraphProperties();
  }

  @Bean
  @ConfigurationProperties("nci.evs.opensearch.query")
  OpensearchQueryProperties queryProperties() {
    return new OpensearchQueryProperties();
  }
}
