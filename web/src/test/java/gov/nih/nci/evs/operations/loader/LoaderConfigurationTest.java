package gov.nih.nci.evs.operations.loader;

import static org.junit.jupiter.api.Assertions.assertEquals;

import gov.nih.nci.evs.api.properties.ApplicationProperties;
import gov.nih.nci.evs.api.properties.GraphProperties;
import org.junit.jupiter.api.Test;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.ConfigDataApplicationContextInitializer;
import org.springframework.boot.test.context.runner.ApplicationContextRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.env.StandardEnvironment;

/** Loader profiles preserve CLI defaults without importing server application settings. */
class LoaderConfigurationTest {
  private final ApplicationContextRunner runner =
      new ApplicationContextRunner()
          .withInitializer(
              context -> {
                context
                    .getEnvironment()
                    .getPropertySources()
                    .remove(StandardEnvironment.SYSTEM_ENVIRONMENT_PROPERTY_SOURCE_NAME);
                new ConfigDataApplicationContextInitializer().initialize(context);
              })
          .withUserConfiguration(Settings.class)
          .withPropertyValues("spring.config.name=loader");

  @Configuration(proxyBeanMethods = false)
  @EnableConfigurationProperties
  static class Settings {
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
  }

  @Test
  void configuredDefaultsRemainUnchanged() {
    runner
        .withPropertyValues("GRAPH_DB_MONTHLY_QUERY_URL=http://monthly.invalid/query")
        .run(
            context -> {
              assertEquals(
                  "https://raw.githubusercontent.com/NCIEVS/evsrestapi-operations/main/config/metadata",
                  context.getBean(ApplicationProperties.class).getConfigBaseUri());
              assertEquals(
                  "1000",
                  context.getEnvironment().getProperty("nci.evs.bulkload.downloadBatchSize"));
              assertEquals(
                  "1000", context.getEnvironment().getProperty("nci.evs.bulkload.indexBatchSize"));
              assertEquals(
                  "http://monthly.invalid/query",
                  context.getBean(GraphProperties.class).getQueryUrl());
              assertEquals(60, context.getBean(GraphProperties.class).getReadTimeout());
            });
  }

  @Test
  void localDefaultsFollowSelectedDatabaseAndDevelopmentMetadata() {
    runner
        .withPropertyValues(
            "spring.profiles.active=local",
            "GRAPH_DB=CTRP",
            "GRAPH_DB_MONTHLY_QUERY_URL=http://server-only.invalid/NCIT2/query")
        .run(
            context -> {
              assertEquals(
                  "https://raw.githubusercontent.com/NCIEVS/evsrestapi-operations/develop/config/metadata",
                  context.getBean(ApplicationProperties.class).getConfigBaseUri());
              assertEquals(
                  "250",
                  context.getEnvironment().getProperty("nci.evs.bulkload.downloadBatchSize"));
              assertEquals(
                  "250", context.getEnvironment().getProperty("nci.evs.bulkload.indexBatchSize"));
              assertEquals(
                  "http://localhost:3030/CTRP/query",
                  context.getBean(GraphProperties.class).getQueryUrl());
              assertEquals(500, context.getBean(GraphProperties.class).getReadTimeout());
              assertEquals(30, context.getBean(GraphProperties.class).getConnectTimeout());
            });
  }

  @Test
  void localEnvironmentOverridesRemainSupported() {
    runner
        .withPropertyValues(
            "spring.profiles.active=local",
            "CONFIG_BASE_URI=file:///example/config/metadata",
            "NCI_EVS_BULK_LOAD_DOWNLOAD_BATCH_SIZE=17",
            "NCI_EVS_BULK_LOAD_INDEX_BATCH_SIZE=19",
            "GRAPH_DB_HOST=graph.invalid",
            "GRAPH_DB_PORT=1234",
            "GRAPH_DB=CTRP",
            "GRAPH_DB_READ_TIMEOUT=77",
            "GRAPH_DB_CONNECT_TIMEOUT=8")
        .run(
            context -> {
              assertEquals(
                  "file:///example/config/metadata",
                  context.getBean(ApplicationProperties.class).getConfigBaseUri());
              assertEquals(
                  "17", context.getEnvironment().getProperty("nci.evs.bulkload.downloadBatchSize"));
              assertEquals(
                  "19", context.getEnvironment().getProperty("nci.evs.bulkload.indexBatchSize"));
              assertEquals(
                  "http://graph.invalid:1234/CTRP/query",
                  context.getBean(GraphProperties.class).getQueryUrl());
              assertEquals(77, context.getBean(GraphProperties.class).getReadTimeout());
              assertEquals(8, context.getBean(GraphProperties.class).getConnectTimeout());
            });
  }
}
