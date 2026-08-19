"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  BookOpen,
  ChevronLeft,
  ChevronRight,
  Menu,
  Search,
} from "lucide-react";
import { type FormEvent, useEffect, useMemo, useState } from "react";

import { ReferenceSidebar } from "@/components/references/reference-sidebar";
import { ReaderGrid, ReaderSkeleton } from "@/components/reader/reader-grid";
import { VersionPicker } from "@/components/reader/version-picker";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api/client";
import type { StructureNode } from "@/types/api";

function initialParameter(name: string) {
  if (typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get(name) ?? "";
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Something went wrong.";
}

function QueryError({
  title,
  error,
  onRetry,
}: {
  title: string;
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <div className="reader-paper flex min-h-72 flex-col items-center justify-center px-6 text-center">
      <span className="flex size-11 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertCircle className="size-5" />
      </span>
      <h2 className="mt-4 font-serif text-2xl">{title}</h2>
      <p className="mt-2 max-w-lg text-sm leading-6 text-muted-foreground">
        {errorMessage(error)}
      </p>
      {onRetry ? (
        <Button className="mt-5" variant="outline" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}

export function ReaderApp() {
  const [textSlug, setTextSlug] = useState(() => initialParameter("text"));
  const [reference, setReference] = useState(() => initialParameter("reference"));
  const [referenceDraft, setReferenceDraft] = useState(
    () => initialParameter("reference") || "Mark 1",
  );
  const [selectedVersions, setSelectedVersions] = useState<string[]>(() =>
    initialParameter("versions")
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean),
  );
  const [hasCustomVersionOrder, setHasCustomVersionOrder] = useState(() =>
    Boolean(initialParameter("versions")),
  );
  const [selectedBookId, setSelectedBookId] = useState("");
  const [navigationOpen, setNavigationOpen] = useState(false);

  const textsQuery = useQuery({
    queryKey: ["texts"],
    queryFn: ({ signal }) => api.texts(signal),
  });
  const versionsQuery = useQuery({
    queryKey: ["versions", textSlug],
    queryFn: ({ signal }) => api.versions(textSlug, signal),
    enabled: Boolean(textSlug),
  });
  const structureQuery = useQuery({
    queryKey: ["structure", textSlug],
    queryFn: ({ signal }) => api.structure(textSlug, signal),
    enabled: Boolean(textSlug),
  });
  const chaptersQuery = useQuery({
    queryKey: ["structure-children", textSlug, selectedBookId],
    queryFn: ({ signal }) => api.children(textSlug, selectedBookId, signal),
    enabled: Boolean(textSlug && selectedBookId),
  });
  const resolutionQuery = useQuery({
    queryKey: ["reference", textSlug, reference],
    queryFn: ({ signal }) => api.resolveReference(textSlug, reference, signal),
    enabled: Boolean(textSlug && reference),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.status < 500) && failureCount < 1,
  });
  const readerQuery = useQuery({
    queryKey: [
      "reader",
      textSlug,
      resolutionQuery.data?.label,
      selectedVersions.join(","),
    ],
    queryFn: ({ signal }) =>
      api.reader(
        textSlug,
        resolutionQuery.data!.label,
        selectedVersions,
        signal,
      ),
    enabled: Boolean(
      textSlug && resolutionQuery.data?.label && selectedVersions.length,
    ),
    placeholderData: (previous) => previous,
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.status < 500) && failureCount < 1,
  });

  const texts = textsQuery.data ?? [];
  const versions = versionsQuery.data ?? [];
  const books = structureQuery.data ?? [];
  const chapters = chaptersQuery.data ?? [];
  const resolvedLabel = resolutionQuery.data?.label ?? reference;

  useEffect(() => {
    if (!textSlug && texts.length) setTextSlug(texts[0].slug);
  }, [textSlug, texts]);

  useEffect(() => {
    if (!versions.length) return;
    const available = new Set(
      versions.filter((version) => version.current_release_id).map((version) => version.slug),
    );
    setSelectedVersions((current) => {
      const valid = current.filter((slug) => available.has(slug));
      if (valid.length) return valid;
      return versions
        .filter((version) => version.current_release_id)
        .toSorted((left, right) => {
          const leftEnglish = left.language.iso_code.toLowerCase() === "en" ? 0 : 1;
          const rightEnglish =
            right.language.iso_code.toLowerCase() === "en" ? 0 : 1;
          return leftEnglish - rightEnglish || left.title.localeCompare(right.title);
        })
        .map((version) => version.slug);
    });
  }, [versions]);

  useEffect(() => {
    if (hasCustomVersionOrder || !readerQuery.data?.versions.length) return;
    const sourceSlugs = new Set(
      readerQuery.data.versions
        .filter((version) => version.roles.includes("default_source"))
        .map((version) => version.slug),
    );
    setSelectedVersions((current) => {
      const next = [
        ...current.filter((slug) => !sourceSlugs.has(slug)),
        ...current.filter((slug) => sourceSlugs.has(slug)),
      ];
      return next.every((slug, index) => slug === current[index]) ? current : next;
    });
  }, [hasCustomVersionOrder, readerQuery.data]);

  useEffect(() => {
    if (!books.length) return;
    const matchingBook = [...books]
      .sort((left, right) => right.title.length - left.title.length)
      .find(
        (book) =>
          resolvedLabel === book.title || resolvedLabel.startsWith(`${book.title} `),
      );
    if (matchingBook && matchingBook.id !== selectedBookId) {
      setSelectedBookId(matchingBook.id);
      return;
    }
    if (!selectedBookId) {
      const defaultBook =
        books.find((book) => textSlug === "bible" && book.title === "Mark") ?? books[0];
      setSelectedBookId(defaultBook.id);
    }
  }, [books, resolvedLabel, selectedBookId, textSlug]);

  useEffect(() => {
    if (!reference && chapters.length) {
      setReference(chapters[0].title);
      setReferenceDraft(chapters[0].title);
    }
  }, [chapters, reference]);

  useEffect(() => {
    if (!textSlug || typeof window === "undefined") return;
    const params = new URLSearchParams();
    params.set("text", textSlug);
    if (reference) params.set("reference", reference);
    if (selectedVersions.length) params.set("versions", selectedVersions.join(","));
    window.history.replaceState(null, "", `?${params.toString()}`);
  }, [reference, selectedVersions, textSlug]);

  const currentChapterIndex = useMemo(
    () =>
      chapters.findIndex(
        (chapter) =>
          resolvedLabel === chapter.title ||
          resolvedLabel.startsWith(`${chapter.title}:`),
      ),
    [chapters, resolvedLabel],
  );

  function changeText(slug: string) {
    setTextSlug(slug);
    setSelectedBookId("");
    setReference("");
    setReferenceDraft("");
    setSelectedVersions([]);
    setHasCustomVersionOrder(false);
  }

  function changeBook(book: StructureNode) {
    setSelectedBookId(book.id);
    setReference("");
    setReferenceDraft("");
  }

  function changeChapter(chapter: StructureNode) {
    setReference(chapter.title);
    setReferenceDraft(chapter.title);
    setNavigationOpen(false);
  }

  function moveChapter(offset: number) {
    const target = chapters[currentChapterIndex + offset];
    if (target) changeChapter(target);
  }

  function submitReference(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = referenceDraft.trim();
    if (value) setReference(value);
  }

  function toggleVersion(slug: string) {
    setSelectedVersions((current) =>
      current.includes(slug)
        ? current.length === 1
          ? current
          : current.filter((value) => value !== slug)
        : [...current, slug],
    );
  }

  function reorderVersions(slugs: string[]) {
    setHasCustomVersionOrder(true);
    setSelectedVersions((current) => {
      const selected = new Set(current);
      const ordered = slugs.filter((slug) => selected.has(slug));
      const included = new Set(ordered);
      return [...ordered, ...current.filter((slug) => !included.has(slug))];
    });
  }

  if (textsQuery.isError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-background p-6">
        <QueryError
          title="The library could not be loaded"
          error={textsQuery.error}
          onRetry={() => void textsQuery.refetch()}
        />
      </main>
    );
  }

  return (
    <div className="app-frame">
      <ReferenceSidebar
        open={navigationOpen}
        texts={texts}
        textSlug={textSlug}
        books={books}
        chapters={chapters}
        selectedBookId={selectedBookId}
        currentReference={resolvedLabel}
        onClose={() => setNavigationOpen(false)}
        onTextChange={changeText}
        onBookChange={changeBook}
        onChapterChange={changeChapter}
      />

      <main className="min-w-0 flex-1">
        <header className="reader-toolbar">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="shrink-0 lg:hidden"
              onClick={() => setNavigationOpen(true)}
              aria-label="Open navigation"
            >
              <Menu className="size-4" />
            </Button>
            <form
              onSubmit={submitReference}
              className="reference-search hidden w-64 items-center md:flex"
            >
              <Search className="ml-3 size-4 shrink-0 text-muted-foreground" />
              <input
                aria-label="Reference"
                value={referenceDraft}
                onChange={(event) => setReferenceDraft(event.target.value)}
                placeholder="Go to a reference…"
                className="min-w-0 flex-1 bg-transparent px-2 py-2 text-sm outline-none"
              />
            </form>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => moveChapter(-1)}
              disabled={currentChapterIndex <= 0}
              aria-label="Previous chapter"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => moveChapter(1)}
              disabled={
                currentChapterIndex < 0 || currentChapterIndex >= chapters.length - 1
              }
              aria-label="Next chapter"
            >
              <ChevronRight className="size-4" />
            </Button>
            <VersionPicker
              versions={versions.filter((version) => version.current_release_id)}
              selected={selectedVersions}
              onToggle={toggleVersion}
            />
          </div>
        </header>

        <div className="reader-workspace">
          <div className="reader-heading">
            <div>
              <div className="flex items-center gap-2">
                <Badge>
                  {readerQuery.data?.text.title ??
                    texts.find((text) => text.slug === textSlug)?.title ??
                    "Library"}
                </Badge>
                {resolutionQuery.data ? (
                  <span className="text-xs text-muted-foreground">
                    {resolutionQuery.data.reference_scheme}
                  </span>
                ) : null}
              </div>
              <h1>{resolvedLabel || "Choose a passage"}</h1>
              <p>
                {readerQuery.data
                  ? `${readerQuery.data.units.length} canonical units · ${readerQuery.data.versions.length} aligned editions`
                  : "Select a section or enter a reference to begin reading."}
              </p>
            </div>
            <div className="heading-mark" aria-hidden="true">
              <BookOpen className="size-5" />
            </div>
          </div>

          <form onSubmit={submitReference} className="reference-search mb-4 flex md:hidden">
            <Search className="ml-3 size-4 shrink-0 text-muted-foreground" />
            <input
              aria-label="Reference"
              value={referenceDraft}
              onChange={(event) => setReferenceDraft(event.target.value)}
              placeholder="Go to a reference…"
              className="min-w-0 flex-1 bg-transparent px-2 py-2.5 text-sm outline-none"
            />
          </form>

          {resolutionQuery.isError ? (
            <QueryError
              title="Reference not found"
              error={resolutionQuery.error}
              onRetry={() => void resolutionQuery.refetch()}
            />
          ) : readerQuery.isError ? (
            <QueryError
              title="The passage could not be loaded"
              error={readerQuery.error}
              onRetry={() => void readerQuery.refetch()}
            />
          ) : readerQuery.data ? (
            <ReaderGrid
              reader={readerQuery.data}
              versionOrder={selectedVersions}
              onVersionOrderChange={reorderVersions}
            />
          ) : (
            <ReaderSkeleton columns={Math.max(selectedVersions.length, 1)} />
          )}

          <footer className="reader-footer">
            <span>Intertext</span>
            <span>Canonical text comparison</span>
            <span>{readerQuery.data?.reference.label ?? "—"}</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
