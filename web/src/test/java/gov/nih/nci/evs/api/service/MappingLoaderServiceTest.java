package gov.nih.nci.evs.api.service;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import gov.nih.nci.evs.api.model.Concept;
import gov.nih.nci.evs.api.model.IncludeParam;
import gov.nih.nci.evs.api.model.Mapping;
import gov.nih.nci.evs.api.model.Terminology;
import gov.nih.nci.evs.api.model.TerminologyMetadata;
import gov.nih.nci.evs.api.support.es.IndexMetadata;
import gov.nih.nci.evs.api.util.TerminologyUtils;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.web.server.ResponseStatusException;

/** Verifies mapping provenance and indexed terminology version selection. */
class MappingLoaderServiceTest {

  @ParameterizedTest
  @CsvSource({
    "ChEBI,chebi,247,235,C1003,CHEBI:22565",
    "HGNC,hgnc,202507,202209,C101091,HGNC:20893"
  })
  void twoColumnMappingsUseCurrentIndexesAndPreserveReleaseMetadata(
      final String mapTarget,
      final String target,
      final String currentVersion,
      final String releaseVersion,
      final String sourceCode,
      final String targetCode)
      throws Exception {
    final MappingLoaderServiceImpl loader = loader();
    final Terminology weekly = terminology("ncit", "26.01a", true, false);
    final Terminology monthly = terminology("ncit", "25.12e", true, true);
    final Terminology previous = terminology(target, releaseVersion, false, false);
    final Terminology current = terminology(target, currentVersion, true, false);
    when(loader.osQueryService.getIndexMetadata(true))
        .thenReturn(List.of(index(weekly), index(previous), index(current), index(monthly)));
    when(loader.osQueryService.getConcept(
            anyString(), any(Terminology.class), any(IncludeParam.class)))
        .thenAnswer(
            invocation -> {
              final Concept concept = new Concept();
              concept.setName(invocation.getArgument(0));
              return Optional.of(concept);
            });
    final String[] metadata =
        ("NCIt_to_"
                + mapTarget
                + "_Mapping,,Jun2021,mapping.html,MappingLoadServiceImpl,ncit,24.08d,"
                + target
                + ","
                + releaseVersion)
            .split(",", -1);
    final String[] originalMetadata = metadata.clone();

    final List<Mapping> mappings = loader.buildMaps(sourceCode + "\t" + targetCode, metadata);

    assertEquals(1, mappings.size());
    assertEquals("25.12e", mappings.get(0).getSourceTerminologyVersion());
    assertEquals(currentVersion, mappings.get(0).getTargetTerminologyVersion());
    assertArrayEquals(originalMetadata, metadata);
    verify(loader.osQueryService).getConcept(eq(sourceCode), eq(monthly), any(IncludeParam.class));
    verify(loader.osQueryService).getConcept(eq(targetCode), eq(current), any(IncludeParam.class));
  }

  @Test
  void preformattedMappingsPreserveTheVersionRecordedInTheData() throws Exception {
    final MappingLoaderServiceImpl loader = loader();
    final String[] metadata =
        "GO_to_NCIt_Mapping,,February2020,mapping.html,MappingLoadServiceImpl,go,2022-07-01,ncit,21.06e"
            .split(",", -1);
    final String mappingData =
        "Source Code\tSource Name\tSource Coding Scheme\tSource Coding Scheme Version\tSource"
            + " Coding Scheme Namespace\tAssociation Name\tREL\tMap Rank\tTarget Code\tTarget"
            + " Name\tTarget Coding Scheme\tTarget Coding Scheme Version\tTarget Coding Scheme"
            + " Namespace\n"
            + "GO:0006919\tSource name\tGO\t23-Mar\tGO\tmapsTo\tmapsTo\t1\tC42784\tTarget"
            + " name\tNCI_Thesaurus\t23.02d\tNCI_Thesaurus";

    final List<Mapping> mappings = loader.buildMaps(mappingData, metadata);

    assertEquals(1, mappings.size());
    assertEquals("23.02d", mappings.get(0).getTargetTerminologyVersion());
    assertEquals("21.06e", metadata[8]);
  }

  @Test
  void twoColumnMappingsRequireTheTargetTerminologyToBeIndexed() throws Exception {
    final MappingLoaderServiceImpl loader = loader();
    when(loader.osQueryService.getIndexMetadata(true))
        .thenReturn(List.of(index(terminology("ncit", "25.12e", true, true))));
    when(loader.osQueryService.getConcept(
            anyString(), any(Terminology.class), any(IncludeParam.class)))
        .thenReturn(Optional.empty());
    final String[] metadata =
        "NCIt_to_ChEBI_Mapping,,Jun2021,mapping.html,MappingLoadServiceImpl,ncit,24.08d,chebi,235"
            .split(",", -1);

    assertThrows(
        ResponseStatusException.class, () -> loader.buildMaps("C1003\tCHEBI:22565", metadata));
  }

  private MappingLoaderServiceImpl loader() {
    final MappingLoaderServiceImpl loader = new MappingLoaderServiceImpl();
    loader.osQueryService = mock(OpensearchQueryService.class);
    loader.termUtils = new TerminologyUtils();
    return loader;
  }

  private Terminology terminology(
      final String name, final String version, final boolean latest, final boolean monthly) {
    final Terminology terminology = new Terminology();
    terminology.setTerminology(name);
    terminology.setVersion(version);
    terminology.setLatest(latest);
    terminology.setTags(monthly ? Map.of("monthly", "true") : Map.of());
    final TerminologyMetadata metadata = new TerminologyMetadata();
    metadata.setUiLabel(name);
    terminology.setMetadata(metadata);
    return terminology;
  }

  private IndexMetadata index(final Terminology terminology) {
    final IndexMetadata metadata = new IndexMetadata();
    metadata.setTerminology(terminology);
    metadata.setCompleted(true);
    return metadata;
  }
}
