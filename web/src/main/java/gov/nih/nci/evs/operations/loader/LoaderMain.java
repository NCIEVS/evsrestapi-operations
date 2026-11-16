package gov.nih.nci.evs.operations.loader;

import gov.nih.nci.evs.api.service.LoaderServiceImpl;
import gov.nih.nci.evs.api.service.SamplingApplication;

/** Separate JVM entry point for operational Java commands. */
public final class LoaderMain {
  private LoaderMain() {}

  public static void main(String[] args) throws Exception {
    if (args.length > 0 && "rrfSample".equals(args[0])) {
      SamplingApplication.main(args);
    } else {
      System.setProperty("spring.config.name", "loader");
      LoaderServiceImpl.main(args);
    }
  }
}
