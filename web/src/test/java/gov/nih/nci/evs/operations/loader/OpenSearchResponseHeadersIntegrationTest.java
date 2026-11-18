package gov.nih.nci.evs.operations.loader;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.ObjectMapper;
import gov.nih.nci.evs.api.configuration.OpensearchConfiguration;
import java.net.URI;
import java.util.Arrays;
import java.util.Map;
import java.util.UUID;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.opensearch.client.Request;
import org.opensearch.client.RestHighLevelClient;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.core.env.MapPropertySource;

/** Explicit local-cluster regression for accumulated delete-by-query task headers. */
@Tag("integration")
@EnabledIfEnvironmentVariable(
    named = "EVS_TEST_OPENSEARCH_URL",
    matches = "http://(127\\.0\\.0\\.1|localhost):[0-9]+")
class OpenSearchResponseHeadersIntegrationTest {
  @Test
  void deletesAcrossMoreThanOneHundredScrollBatches() throws Exception {
    URI endpoint = URI.create(System.getenv("EVS_TEST_OPENSEARCH_URL"));
    String index = "evs_header_limit_test_" + UUID.randomUUID().toString().replace("-", "");
    ObjectMapper mapper = new ObjectMapper();
    try (var context = new AnnotationConfigApplicationContext()) {
      context
          .getEnvironment()
          .getPropertySources()
          .addFirst(
              new MapPropertySource(
                  "header-limit-test",
                  Map.of(
                      "nci.evs.opensearch.server.host", endpoint.getHost(),
                      "nci.evs.opensearch.server.port", endpoint.getPort(),
                      "nci.evs.opensearch.server.scheme", endpoint.getScheme(),
                      "nci.evs.opensearch.timeout", 30000)));
      context.register(OpensearchConfiguration.class);
      context.refresh();
      var client = context.getBean(RestHighLevelClient.class).getLowLevelClient();
      boolean created = false;
      try {
        Request create = new Request("PUT", "/" + index);
        create.setJsonEntity("{\"settings\":{\"number_of_shards\":1,\"number_of_replicas\":0}}");
        client.performRequest(create);
        created = true;
        StringBuilder documents = new StringBuilder();
        for (int i = 0; i < 150; i++) {
          documents
              .append("{\"index\":{\"_index\":\"")
              .append(index)
              .append("\",\"_id\":\"")
              .append(i)
              .append("\"}}\n{\"test\":true}\n");
        }
        Request bulk = new Request("POST", "/_bulk");
        bulk.addParameter("refresh", "true");
        bulk.setJsonEntity(documents.toString());
        var indexed =
            mapper.readTree(EntityUtils.toString(client.performRequest(bulk).getEntity()));
        assertFalse(indexed.path("errors").asBoolean(), indexed.toString());

        Request delete = new Request("POST", "/" + index + "/_delete_by_query");
        delete.addParameter("scroll_size", "1");
        delete.addParameter("refresh", "true");
        delete.setJsonEntity("{\"query\":{\"match_all\":{}}}");
        var response = client.performRequest(delete);
        var result = mapper.readTree(EntityUtils.toString(response.getEntity()));
        assertEquals(150, result.path("deleted").asInt(), result.toString());
        long taskHeaders =
            Arrays.stream(response.getHeaders())
                .filter(header -> "TASK_RESOURCE_USAGE".equalsIgnoreCase(header.getName()))
                .count();
        assertTrue(taskHeaders > 100, "Expected task-resource tracking to exercise the old limit");
        var count =
            mapper.readTree(
                EntityUtils.toString(
                    client
                        .performRequest(new Request("GET", "/" + index + "/_count"))
                        .getEntity()));
        assertEquals(0, count.path("count").asInt());
        System.out.println("Deleted 150 documents with " + taskHeaders + " task-resource headers");
      } finally {
        if (created) {
          client.performRequest(new Request("DELETE", "/" + index));
        }
      }
    }
  }
}
