/** Create / edit a project. One form, two modes, so the fields never drift apart. */

import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useCreateProject, useUpdateProject } from "../api/hooks";
import type { Project, ProjectInput } from "../api/types";
import { useToast } from "../hooks/useToast";
import { PRIORITIES, PROJECT_STATUSES, label } from "../lib/format";
import { Modal } from "./ui/Modal";
import { Button, Field, Input, Select, Textarea } from "./ui/Primitives";
import { InlineError } from "./ui/States";

interface Props {
  open: boolean;
  project?: Project | null;
  onClose: () => void;
}

const EMPTY: ProjectInput = {
  name: "",
  description: "",
  status: "planning",
  priority: "medium",
  repository_url: "",
};

export function ProjectFormModal({ open, project, onClose }: Props) {
  const [form, setForm] = useState<ProjectInput>(EMPTY);
  const createProject = useCreateProject();
  const updateProject = useUpdateProject();
  const { notify } = useToast();

  const mutation = project ? updateProject : createProject;
  const error = mutation.error;

  useEffect(() => {
    if (!open) return;
    mutation.reset();
    setForm(
      project
        ? {
            name: project.name,
            description: project.description ?? "",
            status: project.status,
            priority: project.priority,
            repository_url: project.repository_url ?? "",
          }
        : EMPTY,
    );
    // Resetting only when the dialog opens keeps typing from being clobbered.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, project?.id]);

  function update<K extends keyof ProjectInput>(key: K, value: ProjectInput[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const payload: ProjectInput = {
      ...form,
      name: form.name.trim(),
      description: form.description?.trim() || null,
      repository_url: form.repository_url?.trim() || null,
    };

    try {
      if (project) {
        await updateProject.mutateAsync({ id: project.id, input: payload });
        notify("Project updated.", "success");
      } else {
        await createProject.mutateAsync(payload);
        notify("Project created.", "success");
      }
      onClose();
    } catch {
      // Rendered inline below; the dialog stays open so the input is not lost.
    }
  }

  const fieldError = (field: string) =>
    error instanceof ApiError ? error.fieldError(field) : undefined;

  return (
    <Modal
      open={open}
      title={project ? "Edit project" : "New project"}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose} type="button">
            Cancel
          </Button>
          <Button variant="primary" type="submit" form="project-form" loading={mutation.isPending}>
            {project ? "Save changes" : "Create project"}
          </Button>
        </>
      }
    >
      <form className="modal-body" id="project-form" onSubmit={onSubmit} noValidate>
        {error && !fieldError("name") && <InlineError error={error} />}

        <Field label="Name" htmlFor="project-name" error={fieldError("name")}>
          <Input
            id="project-name"
            value={form.name}
            onChange={(event) => update("name", event.target.value)}
            placeholder="Payments Service"
            required
            autoFocus
          />
        </Field>

        <Field
          label="Description"
          htmlFor="project-description"
          hint="What this project is for. Optional."
        >
          <Textarea
            id="project-description"
            value={form.description ?? ""}
            onChange={(event) => update("description", event.target.value)}
            rows={4}
          />
        </Field>

        <div className="row wrap">
          <Field label="Status" htmlFor="project-status">
            <Select
              id="project-status"
              value={form.status}
              onChange={(event) => update("status", event.target.value as ProjectInput["status"])}
            >
              {PROJECT_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {label(status)}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Priority" htmlFor="project-priority">
            <Select
              id="project-priority"
              value={form.priority}
              onChange={(event) =>
                update("priority", event.target.value as ProjectInput["priority"])
              }
            >
              {PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {label(priority)}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field
          label="Repository URL"
          htmlFor="project-repo"
          hint="Optional. Must be a full URL."
          error={fieldError("repository_url")}
        >
          <Input
            id="project-repo"
            type="url"
            value={form.repository_url ?? ""}
            onChange={(event) => update("repository_url", event.target.value)}
            placeholder="https://github.com/acme/payments"
          />
        </Field>
      </form>
    </Modal>
  );
}
