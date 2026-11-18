package gov.nih.nci.evs.api.service;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import gov.nih.nci.evs.api.model.Terminology;
import gov.nih.nci.evs.api.model.TerminologyMetadata;
import gov.nih.nci.evs.api.model.TerminologyStats;
import gov.nih.nci.evs.api.support.es.IndexMetadata;
import gov.nih.nci.evs.api.support.es.OpensearchLoadConfig;
import gov.nih.nci.evs.api.util.HierarchyUtils;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.springframework.context.ApplicationContext;
import org.springframework.test.util.ReflectionTestUtils;

/** Unit test for {@link BaseLoaderService}. */
public class BaseLoaderServiceTest {

  /**
   * Test compute hierarchy statistics.
   *
   * @throws Exception the exception
   */
  @Test
  public void testComputeHierarchyStatistics() throws Exception {
    final Terminology terminology = terminology(true);
    final HierarchyUtils hierarchy =
        new HierarchyUtils(
            terminology,
            Arrays.asList(
                "A\tRoot A\tB\tChild B",
                "A\tRoot A\tC\tChild C",
                "A\tRoot A\tG\tChild G",
                "B\tChild B\tD\tChild D",
                "B\tChild B\tF\tChild F",
                "C\tChild C\tD\tChild D",
                "C\tChild C\tE\tChild E",
                "D\tChild D\tF\tChild F",
                "E\tChild E\tF\tChild F"));
    final TestLoaderService loader = new TestLoaderService();

    loader.computeHierarchyStatistics(terminology, hierarchy);

    final TerminologyStats stats = loader.getStatistics();
    final TerminologyStats.HierarchyStats hierarchyStats = stats.getHierarchy();
    assertEquals("unit", stats.getTerminology());
    assertEquals("1", stats.getVersion());
    assertEquals(true, hierarchyStats.getApplicable());
    assertEquals(6, hierarchyStats.getCodeCount());
    assertEquals(10, hierarchyStats.getTreePositionCount());
    assertEquals(1, hierarchyStats.getRootCount());
    assertNotNull(hierarchyStats.getMinPaths());
    assertEquals(1, hierarchyStats.getMinPaths().getCount());
    assertEquals("F", hierarchyStats.getMaxPaths().getCode());
    assertEquals("Child F", hierarchyStats.getMaxPaths().getName());
    assertEquals(4, hierarchyStats.getMaxPaths().getCount());
    assertEquals("A", hierarchyStats.getMaxChildren().getCode());
    assertEquals(3, hierarchyStats.getMaxChildren().getCount());
    assertEquals("F", hierarchyStats.getMaxParents().getCode());
    assertEquals(3, hierarchyStats.getMaxParents().getCount());
  }

  /**
   * Test compute hierarchy statistics for a terminology without hierarchy.
   *
   * @throws Exception the exception
   */
  @Test
  public void testComputeHierarchyStatisticsNotApplicable() throws Exception {
    final Terminology terminology = terminology(false);
    final TestLoaderService loader = new TestLoaderService();

    loader.computeHierarchyStatistics(terminology, null);

    final TerminologyStats.HierarchyStats hierarchyStats = loader.getStatistics().getHierarchy();
    assertEquals(false, hierarchyStats.getApplicable());
    assertEquals(0, hierarchyStats.getCodeCount());
    assertEquals(0, hierarchyStats.getTreePositionCount());
    assertEquals(0, hierarchyStats.getRootCount());
    assertNull(hierarchyStats.getMinPaths());
    assertNull(hierarchyStats.getMaxPaths());
    assertNull(hierarchyStats.getMaxChildren());
    assertNull(hierarchyStats.getMaxParents());
  }

  /**
   * Test compute hierarchy statistics clears stale hierarchy values.
   *
   * @throws Exception the exception
   */
  @Test
  public void testComputeHierarchyStatisticsClearsStaleValues() throws Exception {
    final Terminology terminology = terminology(true);
    final HierarchyUtils hierarchy =
        new HierarchyUtils(
            terminology,
            Arrays.asList(
                "A\tRoot A\tB\tChild B", "A\tRoot A\tC\tChild C", "B\tChild B\tD\tChild D"));
    final TestLoaderService loader = new TestLoaderService();

    loader.computeHierarchyStatistics(terminology, hierarchy);
    assertNotNull(loader.getStatistics().getHierarchy().getMaxPaths());

    terminology.getMetadata().setHierarchy(false);
    loader.computeHierarchyStatistics(terminology, hierarchy);

    final TerminologyStats.HierarchyStats hierarchyStats = loader.getStatistics().getHierarchy();
    assertEquals(false, hierarchyStats.getApplicable());
    assertEquals(0, hierarchyStats.getCodeCount());
    assertNull(hierarchyStats.getMaxPaths());
    assertNull(hierarchyStats.getMaxChildren());
    assertNull(hierarchyStats.getMaxParents());
  }

  /** Test welcome-text interpolation from NCIM release metadata. */
  @Test
  public void testWelcomeTextInterpolation() {
    final String welcomeText =
        BaseLoaderService.interpolateWelcomeText(
            "UMLS ${umlsVersion}; NCIt ${umlsNcitVersion}; ${unresolved}",
            Map.of("umlsVersion", "2026AA", "umlsNcitVersion", "25.06e"));

    assertEquals("UMLS 2026AA; NCIt 25.06e; ${unresolved}", welcomeText);
  }

  /** Latest-flag reconciliation preserves the concept statuses belonging to each version. */
  @Test
  public void testUpdateLatestFlagPreservesVersionStatuses() throws Exception {
    final TestLoaderService loader = new TestLoaderService();
    final OpensearchQueryService query = mock(OpensearchQueryService.class);
    loader.operationsService = mock(OpensearchOperationsService.class);
    ReflectionTestUtils.setField(loader, "osQueryService", query);
    final IndexMetadata previous = indexMetadata("25.11d", "monthly", List.of("Header_Concept"));
    final IndexMetadata monthly =
        indexMetadata("25.12e", "monthly", List.of("Header_Concept", "Retired_Concept"));
    final IndexMetadata weekly =
        indexMetadata(
            "26.01a",
            "weekly",
            List.of("Header_Concept", "Retired_Concept", "Provisional_Concept"));
    when(query.getIndexMetadata(true))
        .thenReturn(new ArrayList<>(List.of(previous, monthly, weekly)));

    loader.updateLatestFlag(previous.getTerminology(), Set.of());

    assertEquals(
        List.of("Header_Concept"), previous.getTerminology().getMetadata().getConceptStatuses());
    assertEquals(
        List.of("Header_Concept", "Retired_Concept"),
        monthly.getTerminology().getMetadata().getConceptStatuses());
    assertEquals(
        List.of("Header_Concept", "Retired_Concept", "Provisional_Concept"),
        weekly.getTerminology().getMetadata().getConceptStatuses());
    assertFalse(previous.getTerminology().getLatest());
    assertTrue(monthly.getTerminology().getLatest());
    assertTrue(weekly.getTerminology().getLatest());
    verify(loader.operationsService)
        .bulkIndexAndWait(
            List.of(weekly, monthly, previous),
            OpensearchOperationsService.METADATA_INDEX,
            IndexMetadata.class);
  }

  /** Returns indexed metadata with version-specific concept statuses. */
  private IndexMetadata indexMetadata(
      final String version, final String tag, final List<String> statuses) {
    final Terminology terminology = terminology(true);
    terminology.setVersion(version);
    terminology.setTags(new HashMap<>(Map.of(tag, "true")));
    terminology.getMetadata().setConceptStatuses(new ArrayList<>(statuses));
    final IndexMetadata metadata = new IndexMetadata();
    metadata.setTerminology(terminology);
    return metadata;
  }

  /**
   * Returns a test terminology.
   *
   * @param hierarchy the hierarchy flag
   * @return the test terminology
   */
  private Terminology terminology(final boolean hierarchy) {
    final Terminology terminology = new Terminology();
    terminology.setTerminology("unit");
    terminology.setVersion("1");
    final TerminologyMetadata metadata = new TerminologyMetadata();
    metadata.setHierarchy(hierarchy);
    terminology.setMetadata(metadata);
    return terminology;
  }

  /** Test loader service. */
  private static class TestLoaderService extends BaseLoaderService {

    @Override
    public void loadObjects(
        final OpensearchLoadConfig config,
        final Terminology terminology,
        final HierarchyUtils hierarchy)
        throws IOException, Exception {
      // n/a
    }

    @Override
    public int loadConcepts(
        final OpensearchLoadConfig config,
        final Terminology terminology,
        final HierarchyUtils hierarchy,
        final Map<String, List<Map<String, String>>> historyMap)
        throws IOException, Exception {
      return 0;
    }

    @Override
    public Terminology getTerminology(
        final ApplicationContext app,
        final OpensearchLoadConfig config,
        final String filepath,
        final String termName,
        final boolean forceDelete)
        throws Exception {
      return null;
    }

    @Override
    public HierarchyUtils getHierarchyUtils(final Terminology term) throws Exception {
      return null;
    }
  }
}
