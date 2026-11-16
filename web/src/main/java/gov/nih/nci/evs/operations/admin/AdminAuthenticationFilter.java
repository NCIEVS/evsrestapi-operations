package gov.nih.nci.evs.operations.admin;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Require the configured API key for every request to the private operations service. */
@Component
public class AdminAuthenticationFilter extends OncePerRequestFilter {
  private final String expectedKey;

  public AdminAuthenticationFilter(AdminProperties properties) {
    this.expectedKey = properties.getApiKey();
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest request, HttpServletResponse response, FilterChain chain)
      throws ServletException, IOException {
    String key = request.getParameter("apiKey");
    String expected = expectedKey;
    if (key == null
        || expected == null
        || expected.isBlank()
        || !MessageDigest.isEqual(
            key.getBytes(StandardCharsets.UTF_8), expected.getBytes(StandardCharsets.UTF_8))) {
      response.setStatus(401);
      return;
    }
    chain.doFilter(request, response);
  }
}
