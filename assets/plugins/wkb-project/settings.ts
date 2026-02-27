import type { ProjectInfo } from "./projectService";

export interface WkbProjectSettings {
  activeProject?: ProjectInfo;
}

export const DEFAULT_SETTINGS: WkbProjectSettings = {};
