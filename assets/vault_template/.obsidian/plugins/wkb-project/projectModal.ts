import { App, Notice, SuggestModal } from "obsidian";
import type { ProjectInfo } from "./projectService";

export class ProjectModal extends SuggestModal<ProjectInfo> {
  constructor(
    app: App,
    private readonly projects: ProjectInfo[],
    private readonly onSelect: (project: ProjectInfo) => void
  ) {
    super(app);
    this.setPlaceholder("Select active project...");
  }

  open(): void {
    if (this.projects.length === 0) {
      new Notice("WKB Project Plugin: No project folders found in /projects.");
      return;
    }

    super.open();
  }

  getSuggestions(query: string): ProjectInfo[] {
    const normalized = query.toLowerCase().trim();
    if (!normalized) {
      return this.projects;
    }

    return this.projects.filter((project) =>
      project.name.toLowerCase().includes(normalized)
    );
  }

  renderSuggestion(project: ProjectInfo, el: HTMLElement): void {
    el.setText(project.name);
  }

  onChooseSuggestion(project: ProjectInfo): void {
    this.onSelect(project);
  }
}
