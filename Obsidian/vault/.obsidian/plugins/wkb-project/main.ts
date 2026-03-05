import { Notice, Plugin } from "obsidian";
import { ProjectModal } from "./projectModal";
import { ProjectService } from "./projectService";
import type { ProjectInfo } from "./projectService";
import { DEFAULT_SETTINGS, type WkbProjectSettings } from "./settings";

const ROOT_MODE_PROJECT: ProjectInfo = {
  name: "__root__",
  path: "",
};

export default class WkbProjectPlugin extends Plugin {
  private settings: WkbProjectSettings = DEFAULT_SETTINGS;
  private projectService!: ProjectService;
  private statusBarEl!: HTMLElement;

  async onload(): Promise<void> {
    this.projectService = new ProjectService(this.app);
    await this.loadSettings();

    this.statusBarEl = this.addStatusBarItem();
    this.statusBarEl.addClass("mod-clickable");
    this.statusBarEl.addEventListener("click", () => {
      this.openProjectSelector();
    });

    this.addCommand({
      id: "wkb-set-active-project",
      name: "WKB: Set Active Project",
      callback: () => {
        this.openProjectSelector();
      },
    });

    this.app.workspace.onLayoutReady(() => {
      void this.applyStartupMode();
    });
  }

  onunload(): void {}

  getActiveProject(): ProjectInfo | null {
    return this.settings.activeProject ?? null;
  }

  setActiveProject(project: ProjectInfo): void {
    if (!this.projectService.hasProjectsRoot()) {
      this.setRootModeActiveProject();
      return;
    }

    const validProjects = this.projectService.listProjects();
    const isValidProject = validProjects.some(
      (candidate) => candidate.path === project.path
    );
    if (!isValidProject) {
      new Notice("WKB Project Plugin: Project must be a first-level /projects folder.");
      return;
    }

    this.settings.activeProject = project;
    this.updateStatusBar();
    void this.saveSettings();
  }

  private async loadSettings(): Promise<void> {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
  }

  private async saveSettings(): Promise<void> {
    await this.saveData(this.settings);
  }

  private updateStatusBar(): void {
    if (!this.projectService.hasProjectsRoot()) {
      this.statusBarEl.setText("Project: Root");
      return;
    }

    const active = this.getActiveProject();
    if (!active) {
      this.statusBarEl.setText("Project: None");
      return;
    }

    this.statusBarEl.setText(`Project: ${active.name}`);
  }

  private openProjectSelector(): void {
    if (!this.projectService.hasProjectsRoot()) {
      this.setRootModeActiveProject();
      new Notice("WKB Project Plugin: /projects missing. Root Mode active.");
      return;
    }

    const projects = this.projectService.listProjects();
    const modal = new ProjectModal(this.app, projects, (selectedProject) => {
      this.setActiveProject(selectedProject);
    });
    modal.open();
  }

  private async applyStartupMode(): Promise<void> {
    if (!this.projectService.hasProjectsRoot()) {
      this.setRootModeActiveProject();
      return;
    }

    const projects = this.projectService.listProjects();
    const active = this.getActiveProject();
    const hasValidActiveProject =
      active !== null &&
      projects.some((candidate) => candidate.path === active.path);

    if (hasValidActiveProject) {
      this.updateStatusBar();
      return;
    }

    if (active && this.isRootModeProject(active)) {
      this.settings.activeProject = undefined;
      await this.saveSettings();
    }

    this.updateStatusBar();
    if (projects.length > 0) {
      this.openProjectSelector();
    }
  }

  private setRootModeActiveProject(): void {
    if (!this.isRootModeProject(this.getActiveProject())) {
      this.settings.activeProject = ROOT_MODE_PROJECT;
      void this.saveSettings();
    }
    this.updateStatusBar();
  }

  private isRootModeProject(project: ProjectInfo | null): boolean {
    return project?.name === ROOT_MODE_PROJECT.name && project.path === ROOT_MODE_PROJECT.path;
  }
}
