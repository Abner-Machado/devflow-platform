/** Create / edit a task. */

import { useEffect, useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { useCreateTask, useProjects, useUpdateTask } from "../api/hooks";
import type { Task, TaskInput } from "../api/types";
import { useToast } from "../hooks/useToast";
import {
  PRIORITIES,
  TASK_STATUSES,
  fromDateTimeLocal,
  label,
  toDateTimeLocal,
} from "../lib/format";
import { Modal } from "./ui/Modal";
import { Button, Field, Input, Select, Textarea } from "./ui/Primitives";
import { InlineError } from "./ui/States";

interface Props {
  open: boolean;
  task?: Task | null;
  defaultProjectId?: string;
  onClose: () => void;
}

interface FormState {
  title: string;
  description: string;
  status: TaskInput["status"];
  priority: TaskInput["priority"];
  project_id: string;
  due_date: string;
}

const EMPTY: FormState = {
  title: "",
  description: "",
  status: "todo",
  priority: "medium",
  project_id: "",
  due_date: "",
};

export function TaskFormModal({ open, task, defaultProjectId, onClose }: Props) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const projects = useProjects({ page_size: 100, sort_by: "name", order: "asc" });
  const createTask = useCreateTask();
  const updateTask = useUpdateTask();
  const { notify } = useToast();

  const mutation = task ? updateTask : createTask;
  const error = mutation.error;

  useEffect(() => {
    if (!open) return;
    mutation.reset();
    setForm(
      task
        ? {
            title: task.title,
            description: task.description ?? "",
            status: task.status,
            priority: task.priority,
            project_id: task.project_id,
            due_date: toDateTimeLocal(task.due_date),
          }
        : { ...EMPTY, project_id: defaultProjectId ?? "" },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, task?.id, defaultProjectId]);

  // A brand new task needs a project; default to the first one available.
  useEffect(() => {
    if (!open || task || form.project_id) return;
    const first = projects.data?.items[0];
    if (first) setForm((current) => ({ ...current, project_id: first.id }));
  }, [open, task, form.project_id, projects.data]);

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const payload: TaskInput = {
      title: form.title.trim(),
      description: form.description.trim() || null,
      status: form.status,
      priority: form.priority,
      project_id: form.project_id,
      due_date: fromDateTimeLocal(form.due_date),
    };

    try {
      if (task) {
        await updateTask.mutateAsync({ id: task.id, input: payload });
        notify("Task updated.", "success");
      } else {
        await createTask.mutateAsync(payload);
        notify("Task created.", "success");
      }
      onClose();
    } catch {
      // Surfaced inline.
    }
  }

  const fieldError = (field: string) =>
    error instanceof ApiError ? error.fieldError(field) : undefined;
  const noProjects = !projects.isLoading && (projects.data?.items.length ?? 0) === 0;

  return (
    <Modal
      open={open}
      title={task ? "Edit task" : "New task"}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose} type="button">
            Cancel
          </Button>
          <Button
            variant="primary"
            type="submit"
            form="task-form"
            loading={mutation.isPending}
            disabled={noProjects}
          >
            {task ? "Save changes" : "Create task"}
          </Button>
        </>
      }
    >
      <form className="modal-body" id="task-form" onSubmit={onSubmit} noValidate>
        {noProjects && (
          <p className="inline-error">Create a project first - every task belongs to one.</p>
        )}
        {error && <InlineError error={error} />}

        <Field label="Title" htmlFor="task-title" error={fieldError("title")}>
          <Input
            id="task-title"
            value={form.title}
            onChange={(event) => update("title", event.target.value)}
            placeholder="Handle failed webhook retries"
            required
            autoFocus
          />
        </Field>

        <Field label="Description" htmlFor="task-description">
          <Textarea
            id="task-description"
            value={form.description}
            onChange={(event) => update("description", event.target.value)}
            rows={3}
          />
        </Field>

        <Field label="Project" htmlFor="task-project" error={fieldError("project_id")}>
          <Select
            id="task-project"
            value={form.project_id}
            onChange={(event) => update("project_id", event.target.value)}
            required
          >
            {projects.data?.items.map((project) => (
              <option key={project.id} value={project.id}>
                {project.name}
              </option>
            ))}
          </Select>
        </Field>

        <div className="row wrap">
          <Field label="Status" htmlFor="task-status">
            <Select
              id="task-status"
              value={form.status}
              onChange={(event) => update("status", event.target.value as FormState["status"])}
            >
              {TASK_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {label(status)}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Priority" htmlFor="task-priority">
            <Select
              id="task-priority"
              value={form.priority}
              onChange={(event) => update("priority", event.target.value as FormState["priority"])}
            >
              {PRIORITIES.map((priority) => (
                <option key={priority} value={priority}>
                  {label(priority)}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field label="Due date" htmlFor="task-due" hint="Optional.">
          <Input
            id="task-due"
            type="datetime-local"
            value={form.due_date}
            onChange={(event) => update("due_date", event.target.value)}
          />
        </Field>
      </form>
    </Modal>
  );
}
