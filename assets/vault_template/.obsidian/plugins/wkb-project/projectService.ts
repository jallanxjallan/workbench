import { App, TFolder } from "obsidian";

export interface ProjectInfo {
  name: string;
  path: string;
}

export class ProjectService {
  constructor(private readonly app: App) {}

  getProjectsRoot(): TFolder | null {
    const root = this.app.vault.getAbstractFileByPath("projects");
    return root instanceof TFolder ? root : null;
  }

  hasProjectsRoot(): boolean {
    return this.getProjectsRoot() !== null;
  }

  listProjects(): ProjectInfo[] {
    const projectsRoot = this.getProjectsRoot();
    if (!projectsRoot) {
      return [];
    }

    return projectsRoot.children
      .filter((child): child is TFolder => child instanceof TFolder)
      .map((folder) => ({
        name: folder.name,
        path: folder.path,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }
}
