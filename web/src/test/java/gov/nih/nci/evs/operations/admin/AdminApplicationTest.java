package gov.nih.nci.evs.operations.admin;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.context.ApplicationContext;
import org.springframework.test.context.DynamicPropertyRegistry;
import org.springframework.test.context.DynamicPropertySource;
import org.springframework.test.web.servlet.MockMvc;

/** Confirms the private service starts and authenticates without backend services. */
@SpringBootTest(classes = AdminApplication.class)
@AutoConfigureMockMvc
class AdminApplicationTest {
  private static final String KEY = "test-key-0123456789abcdef0123456789";
  private static final Path state;

  static {
    try {
      state = Files.createTempDirectory("operations-api-test");
    } catch (Exception e) {
      throw new ExceptionInInitializerError(e);
    }
  }

  @DynamicPropertySource
  static void properties(DynamicPropertyRegistry registry) {
    registry.add("admin.api-key", () -> KEY);
    registry.add("admin.state-dir", state::toString);
  }

  @Autowired MockMvc mvc;
  @Autowired ApplicationContext context;

  @Test
  void startsWithoutBackendBeans() {
    assertEquals(state, context.getBean(AdminProperties.class).getStateDir());
    assertFalse(context.containsBean("client"));
    assertFalse(context.containsBean("graphOpensearchLoadServiceImpl"));
    assertFalse(context.containsBean("fhirConfig"));
  }

  @Test
  void protectsAllRoutesAndValidatesCommands() throws Exception {
    for (String path :
        new String[] {
          "/admin/commands",
          "/admin/processes",
          "/admin/processes/missing",
          "/admin/processes/missing/log"
        }) {
      mvc.perform(get(path)).andExpect(status().isUnauthorized());
      mvc.perform(get(path).param("apiKey", "wrong")).andExpect(status().isUnauthorized());
    }
    mvc.perform(post("/admin/exec").contentType("application/json").content("{}"))
        .andExpect(status().isUnauthorized());
    mvc.perform(get("/admin/commands").param("apiKey", KEY)).andExpect(status().isOk());
    mvc.perform(
            post("/admin/exec")
                .param("apiKey", KEY)
                .contentType("application/json")
                .content("{\"command\":\"../../bin/bash\",\"args\":[]}"))
        .andExpect(status().isBadRequest());
  }

  @Test
  void protectsEncodedAdminPaths() throws Exception {
    for (String prefix : new String[] {"/%61dmin", "/a%64min", "/ad%6din"}) {
      for (String suffix :
          new String[] {
            "/commands", "/processes", "/processes/missing", "/processes/missing/log"
          }) {
        URI uri = URI.create(prefix + suffix);
        mvc.perform(get(uri)).andExpect(status().isUnauthorized());
        mvc.perform(get(uri).param("apiKey", "wrong")).andExpect(status().isUnauthorized());
      }
      mvc.perform(get(URI.create(prefix + "/commands")).param("apiKey", KEY))
          .andExpect(status().isOk());
      URI exec = URI.create(prefix + "/exec");
      mvc.perform(post(exec).contentType("application/json").content("{}"))
          .andExpect(status().isUnauthorized());
      mvc.perform(post(exec).param("apiKey", "wrong").contentType("application/json").content("{}"))
          .andExpect(status().isUnauthorized());
      mvc.perform(
              post(exec)
                  .param("apiKey", KEY)
                  .contentType("application/json")
                  .content("{\"command\":\"unknown\",\"args\":[]}"))
          .andExpect(status().isBadRequest());
    }
  }

  @Test
  void protectsUnmappedPaths() throws Exception {
    for (String path : new String[] {"/", "/health", "/not-a-route"}) {
      mvc.perform(get(path)).andExpect(status().isUnauthorized());
      mvc.perform(get(path).param("apiKey", "wrong")).andExpect(status().isUnauthorized());
    }
    mvc.perform(get("/not-a-route").param("apiKey", KEY)).andExpect(status().isNotFound());
  }

  @Test
  void acceptsTheKeyInAHeader() throws Exception {
    mvc.perform(get("/admin/commands").header("X-Admin-Key", KEY)).andExpect(status().isOk());
    mvc.perform(get("/admin/commands").header("X-Admin-Key", "wrong"))
        .andExpect(status().isUnauthorized());
    // A wrong header is not rescued by a correct parameter.
    mvc.perform(get("/admin/commands").header("X-Admin-Key", "wrong").param("apiKey", KEY))
        .andExpect(status().isUnauthorized());
  }
}
