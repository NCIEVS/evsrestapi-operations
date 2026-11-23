package gov.nih.nci.evs.api.service;

import static org.assertj.core.api.Assertions.assertThat;

import gov.nih.nci.evs.api.model.TerminologyMetadata;
import gov.nih.nci.evs.api.util.ThreadLocalMapper;
import gov.nih.nci.evs.operations.loader.LoaderApplication;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/** Metadata loading regression moved with its loader dependency. */
@Tag("integration")
@SpringBootTest(
    classes = LoaderApplication.class,
    webEnvironment = SpringBootTest.WebEnvironment.NONE)
class LoaderMetadataIntegrationTest {
  @Autowired private GraphOpensearchLoadServiceImpl loader;

  @Test
  void metadataReading() throws Exception {
    TerminologyMetadata metadata =
        ThreadLocalMapper.get()
            .treeToValue(loader.getMetadataAsNodeLocal("ncit"), TerminologyMetadata.class);
    assertThat(metadata.getExtraSubsets()).isNotEmpty();
  }
}
