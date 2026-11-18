package gov.nih.nci.evs.operations.loader;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import org.junit.jupiter.api.Test;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;

/** Confirms the loader builds a non-web context without server or FHIR components. */
class LoaderContextTest {
  @TestConfiguration
  static class Backend {
    @Bean
    @Primary
    org.opensearch.client.RestHighLevelClient mockClient() {
      return mock(org.opensearch.client.RestHighLevelClient.class);
    }
  }

  @Test
  void startsWithOnlyLoaderComponents() {
    try (var context =
        new SpringApplicationBuilder(LoaderApplication.class, Backend.class)
            .web(WebApplicationType.NONE)
            .properties("spring.config.name=loader", "spring.main.banner-mode=off")
            .run()) {
      assertTrue(context.containsBean("graphOpensearchLoadServiceImpl"));
      assertFalse(context.containsBean("adminController"));
      assertFalse(context.containsBean("fhirConfig"));
      assertFalse(context.containsBean("dispatcherServlet"));
    }
  }
}
