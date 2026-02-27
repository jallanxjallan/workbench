"use strict";

const { Notice, Plugin, SuggestModal, TFolder } = require("obsidian");
const ROOT_MODE_PROJECT = { name: "__root__", path: "" };

class ProjectService {
  constructor(app) {
    this.app = app;
  }

  getProjectsRoot() {
    const root = this.app.vault.getAbstractFileByPath("projects");
    return root instanceof TFolder ? root : null;
  }

  hasProjectsRoot() {
    return this.getProjectsRoot() !== null;
  }

  listProjects() {
    const projectsRoot = this.getProjectsRoot();
    if (!projectsRoot) {
      return [];
    }

    return projectsRoot.children
      .filter((child) => child instanceof TFolder)
      .map((folder) => ({ name: folder.name, path: folder.path }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }
}

class ProjectModal extends SuggestModal {
  constructor(app, projects, onSelect) {
    super(app);
    this.projects = projects;
    this.onSelect = onSelect;
    this.setPlaceholder("Select active project...");
  }

  open() {
    if (this.projects.length === 0) {
      new Notice("WKB Project Plugin: No project folders found in /projects.");
      return;
    }

    super.open();
  }

  getSuggestions(query) {
    const normalized = query.toLowerCase().trim();
    if (!normalized) {
      return this.projects;
    }

    return this.projects.filter((project) =>
      project.name.toLowerCase().includes(normalized)
    );
  }

  renderSuggestion(project, el) {
    el.setText(project.name);
  }

  onChooseSuggestion(project) {
    this.onSelect(project);
  }
}

class WkbProjectPlugin extends Plugin {
  async onload() {
    this.settings = {};
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

  onunload() {}

  getActiveProject() {
    return this.settings.activeProject || null;
  }

  setActiveProject(project) {
    if (!this.projectService.hasProjectsRoot()) {
      this.setRootModeActiveProject();
      return;
    }

    const validProjects = this.projectService.listProjects();
    const isValidProject = validProjects.some(
      (candidate) => candidate.path === project.path
    );
    if (!isValidProject) {
      new Notice(
        "WKB Project Plugin: Project must be a first-level /projects folder."
      );
      return;
    }

    this.settings.activeProject = project;
    this.updateStatusBar();
    void this.saveSettings();
  }

  async loadSettings() {
    this.settings = Object.assign({}, await this.loadData());
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }

  updateStatusBar() {
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

  openProjectSelector() {
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

  async applyStartupMode() {
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
      this.settings.activeProject = void 0;
      await this.saveSettings();
    }

    this.updateStatusBar();
    if (projects.length > 0) {
      this.openProjectSelector();
    }
  }

  setRootModeActiveProject() {
    if (!this.isRootModeProject(this.getActiveProject())) {
      this.settings.activeProject = ROOT_MODE_PROJECT;
      void this.saveSettings();
    }
    this.updateStatusBar();
  }

  isRootModeProject(project) {
    return (
      (project == null ? void 0 : project.name) === ROOT_MODE_PROJECT.name &&
      project.path === ROOT_MODE_PROJECT.path
    );
  }
}

module.exports = WkbProjectPlugin;
