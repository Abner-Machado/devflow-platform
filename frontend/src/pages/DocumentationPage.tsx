/** Markdown documentation: a searchable list on the left, the rendered doc on the right. */

import { useEffect, useState, type FormEvent } from "react";

import {
  useCreateDocument,
  useDeleteDocument,
  useDocument,
  useDocuments,
  useProjects,
  useUpdateDocument,
} from "../api/hooks";
import { IconPlus } from "../components/Icons";
import { Markdown } from "../components/Markdown";
import { ConfirmDialog, Modal } from "../components/ui/Modal";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  Field,
  Input,
  Select,
  Textarea,
} from "../components/ui/Primitives";
import { EmptyState, ErrorState, InlineError, LoadingRows } from "../components/ui/States";
import { useToast } from "../hooks/useToast";
import { formatRelative } from "../lib/format";

interface EditorState {
  id: string | null;
  title: string;
  content: string;
  projectId: string;
}

export function DocumentationPage() {
  const [search, setSearch] = useState("");
  const [projectId, setProjectId] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [deleting, setDeleting] = useState(false);

  const projects = useProjects({ page_size: 100, sort_by: "name", order: "asc" });
  const list = useDocuments({
    search: search || undefined,
    project_id: projectId || undefined,
  });
  const detail = useDocument(selectedId ?? undefined);
  const createDocument = useCreateDocument();
  const updateDocument = useUpdateDocument();
  const deleteDocument = useDeleteDocument();
  const { notify } = useToast();

  // Keep a document selected as the filtered list changes underneath.
  useEffect(() => {
    const items = list.data?.items ?? [];
    if (items.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !items.some((item) => item.id === selectedId)) {
      setSelectedId(items[0].id);
    }
  }, [list.data, selectedId]);

  function openEditor(mode: "new" | "edit") {
    if (mode === "edit" && detail.data) {
      setEditor({
        id: detail.data.id,
        title: detail.data.title,
        content: detail.data.content,
        projectId: detail.data.project_id,
      });
      return;
    }
    setEditor({
      id: null,
      title: "",
      content: "# New document\n\n",
      projectId: projectId || projects.data?.items[0]?.id || "",
    });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!editor) return;

    try {
      if (editor.id) {
        await updateDocument.mutateAsync({
          id: editor.id,
          input: { title: editor.title.trim(), content: editor.content },
        });
        notify("Document saved.", "success");
      } else {
        const created = await createDocument.mutateAsync({
          title: editor.title.trim(),
          content: editor.content,
          project_id: editor.projectId,
        });
        setSelectedId(created.id);
        notify("Document created.", "success");
      }
      setEditor(null);
    } catch {
      // Shown inline in the dialog.
    }
  }

  async function confirmDelete() {
    if (!selectedId) return;
    try {
      await deleteDocument.mutateAsync(selectedId);
      setSelectedId(null);
      notify("Document deleted.", "success");
    } catch {
      notify("Could not delete the document.", "error");
    } finally {
      setDeleting(false);
    }
  }

  const mutation = editor?.id ? updateDocument : createDocument;
  const noProjects = !projects.isLoading && (projects.data?.items.length ?? 0) === 0;

  return (
    <>
      <header className="page-header">
        <div>
          <h1>Documentation</h1>
          <p>Markdown notes attached to the project they describe.</p>
        </div>
        <Button variant="primary" onClick={() => openEditor("new")} disabled={noProjects}>
          <IconPlus />
          New document
        </Button>
      </header>

      <div className="grid grid-split">
        <Card>
          <CardHeader
            title={detail.data?.title ?? "Document"}
            action={
              detail.data && (
                <div className="row">
                  <Button size="sm" onClick={() => openEditor("edit")}>
                    Edit
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setDeleting(true)}>
                    Delete
                  </Button>
                </div>
              )
            }
          />
          <CardBody>
            {detail.isError ? (
              <ErrorState error={detail.error} onRetry={() => void detail.refetch()} />
            ) : detail.isLoading && selectedId ? (
              <LoadingRows rows={6} />
            ) : detail.data ? (
              <>
                <p className="subtle" style={{ marginBottom: "var(--space-4)" }}>
                  {detail.data.project_name} - updated {formatRelative(detail.data.updated_at)}
                  {detail.data.author ? ` by ${detail.data.author.full_name}` : ""}
                </p>
                <Markdown content={detail.data.content} />
              </>
            ) : (
              <EmptyState
                title="Nothing selected"
                description="Pick a document from the list, or write a new one."
              />
            )}
          </CardBody>
        </Card>

        <Card>
          <div className="filter-bar">
            <Input
              className="search"
              type="search"
              placeholder="Search documents"
              aria-label="Search documents"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <Select
              aria-label="Filter by project"
              value={projectId}
              onChange={(event) => setProjectId(event.target.value)}
            >
              <option value="">All projects</option>
              {projects.data?.items.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </Select>
          </div>

          {list.isError ? (
            <ErrorState error={list.error} onRetry={() => void list.refetch()} />
          ) : list.isLoading ? (
            <LoadingRows />
          ) : list.data && list.data.items.length > 0 ? (
            <div className="doc-list">
              {list.data.items.map((document) => (
                <button
                  type="button"
                  key={document.id}
                  className={
                    document.id === selectedId ? "doc-item is-active" : "doc-item"
                  }
                  onClick={() => setSelectedId(document.id)}
                  aria-current={document.id === selectedId}
                >
                  <span style={{ minWidth: 0 }}>
                    <span className="cell-strong truncate" style={{ display: "block" }}>
                      {document.title}
                    </span>
                    <span className="subtle truncate" style={{ display: "block" }}>
                      {document.excerpt || "Empty document"}
                    </span>
                  </span>
                  <span className="subtle">{formatRelative(document.updated_at)}</span>
                </button>
              ))}
            </div>
          ) : search || projectId ? (
            <EmptyState title="No documents match" description="Try another search term." />
          ) : (
            <EmptyState
              title="No documentation yet"
              description="Architecture notes, runbooks, decisions - anything worth keeping."
              action={
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => openEditor("new")}
                  disabled={noProjects}
                >
                  Write the first one
                </Button>
              }
            />
          )}
        </Card>
      </div>

      <Modal
        open={Boolean(editor)}
        wide
        title={editor?.id ? "Edit document" : "New document"}
        onClose={() => setEditor(null)}
        footer={
          <>
            <Button type="button" onClick={() => setEditor(null)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              form="document-form"
              loading={mutation.isPending}
            >
              Save
            </Button>
          </>
        }
      >
        {editor && (
          <form className="modal-body" id="document-form" onSubmit={onSubmit} noValidate>
            {mutation.error && <InlineError error={mutation.error} />}

            <Field label="Title" htmlFor="document-title">
              <Input
                id="document-title"
                value={editor.title}
                onChange={(event) =>
                  setEditor((current) =>
                    current ? { ...current, title: event.target.value } : current,
                  )
                }
                placeholder="Architecture overview"
                required
                autoFocus
              />
            </Field>

            {!editor.id && (
              <Field label="Project" htmlFor="document-project">
                <Select
                  id="document-project"
                  value={editor.projectId}
                  onChange={(event) =>
                    setEditor((current) =>
                      current ? { ...current, projectId: event.target.value } : current,
                    )
                  }
                  required
                >
                  {projects.data?.items.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}

            <Field label="Content" htmlFor="document-content" hint="Markdown is supported.">
              <Textarea
                id="document-content"
                value={editor.content}
                onChange={(event) =>
                  setEditor((current) =>
                    current ? { ...current, content: event.target.value } : current,
                  )
                }
                rows={16}
                style={{ fontFamily: "var(--font-mono)" }}
              />
            </Field>
          </form>
        )}
      </Modal>

      <ConfirmDialog
        open={deleting}
        title="Delete document"
        message={`"${detail.data?.title}" will be removed permanently.`}
        loading={deleteDocument.isPending}
        onConfirm={() => void confirmDelete()}
        onCancel={() => setDeleting(false)}
      />
    </>
  );
}
