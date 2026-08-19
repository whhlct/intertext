"use client";

import { GripVertical, Languages } from "lucide-react";
import { type CSSProperties, type DragEvent, type KeyboardEvent, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ReaderResponse, ReaderSegment, ReaderToken, ReaderTokenGloss } from "@/types/api";

function preferredGloss(token: ReaderToken): ReaderTokenGloss | undefined {
  return (
    token.glosses.find(
      (gloss) => gloss.language.iso_code === "en" && gloss.gloss_type === "contextual",
    ) ??
    token.glosses.find((gloss) => gloss.language.iso_code === "en") ??
    token.glosses.find((gloss) => gloss.gloss_type === "contextual") ??
    token.glosses[0]
  );
}

function tokenSurface(segment: ReaderSegment, tokenIndex: number): string {
  const tokens = segment.tokens ?? [];
  const token = tokens[tokenIndex];
  if (token.char_start === null || token.char_end === null) return token.surface;
  const previousEnd = tokens[tokenIndex - 1]?.char_end;
  const nextStart = tokens[tokenIndex + 1]?.char_start;
  const before = segment.text.slice(previousEnd ?? 0, token.char_start);
  const after = segment.text.slice(token.char_end, nextStart ?? segment.text.length);
  // Punctuation adjacent to the previous word is its suffix; punctuation after
  // whitespace and adjacent to this word is its prefix (for example SBLGNT ⸀).
  const prefix =
    tokenIndex === 0 || (before.startsWith(" ") && !before.endsWith(" "))
      ? before.trim()
      : "";
  const suffix =
    nextStart === undefined || (after.length > 0 && !after.startsWith(" "))
      ? after.trim()
      : "";
  return `${prefix}${token.surface}${suffix}`;
}

function InterlinearSegment({ segment }: { segment: ReaderSegment }) {
  const tokens = segment.tokens ?? [];
  const hasGlosses = tokens.some((token) => preferredGloss(token));
  if (!hasGlosses) return <>{segment.text}</>;

  return (
    <span className="reader-interlinear" aria-label={segment.text}>
      {tokens.map((token, index) => {
        const gloss = preferredGloss(token);
        return (
          <span className="reader-interlinear-token" key={token.id}>
            <span className="reader-token-surface">{tokenSurface(segment, index)}</span>
            {gloss ? (
              <span
                className="reader-token-gloss"
                lang={gloss.language.iso_code}
                title={`${gloss.source} ${gloss.gloss_type} gloss`}
              >
                {gloss.gloss}
              </span>
            ) : null}
          </span>
        );
      })}
    </span>
  );
}

export function ReaderSkeleton({ columns = 2 }: { columns?: number }) {
  return (
    <div className="reader-paper">
      <div className="space-y-0">
        {Array.from({ length: 7 }, (_, index) => (
          <div className="flex gap-6 border-b border-border/65 px-5 py-6" key={index}>
            <Skeleton className="mt-1 size-7 rounded-full" />
            <div
              className="grid flex-1 gap-8"
              style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}
            >
              {Array.from({ length: columns }, (_, column) => (
                <div className="space-y-2" key={column}>
                  <Skeleton className="h-4 w-[92%]" />
                  <Skeleton className="h-4 w-[78%]" />
                  <Skeleton className="h-4 w-[55%]" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

interface ReaderGridProps {
  reader: ReaderResponse;
  versionOrder?: string[];
  onVersionOrderChange?: (slugs: string[]) => void;
}

export function ReaderGrid({
  reader,
  versionOrder = reader.versions.map((version) => version.slug),
  onVersionOrderChange,
}: ReaderGridProps) {
  const [draggedSlug, setDraggedSlug] = useState<string | null>(null);
  const [dropTargetSlug, setDropTargetSlug] = useState<string | null>(null);
  const orderIndex = new Map(versionOrder.map((slug, index) => [slug, index]));
  const requestedOrder = reader.versions.toSorted((left, right) => {
    const leftIndex = orderIndex.get(left.slug) ?? Number.MAX_SAFE_INTEGER;
    const rightIndex = orderIndex.get(right.slug) ?? Number.MAX_SAFE_INTEGER;
    return leftIndex - rightIndex;
  });
  const orderedVersions = requestedOrder;
  const columnStyle = {
    "--reader-columns": Math.max(orderedVersions.length, 1),
  } as CSSProperties;

  if (!reader.units.length) {
    return (
      <div className="reader-paper flex min-h-80 flex-col items-center justify-center px-6 text-center">
        <Languages className="size-8 text-muted-foreground" />
        <h2 className="mt-4 font-serif text-2xl">No units in this range</h2>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          The reference resolved successfully, but it does not contain readable canonical units.
        </p>
      </div>
    );
  }

  function moveVersion(sourceSlug: string, targetSlug: string) {
    if (sourceSlug === targetSlug || !onVersionOrderChange) return;
    const reordered = [...orderedVersions];
    const sourceIndex = reordered.findIndex((version) => version.slug === sourceSlug);
    const targetIndex = reordered.findIndex((version) => version.slug === targetSlug);
    if (sourceIndex < 0 || targetIndex < 0) return;
    const [moved] = reordered.splice(sourceIndex, 1);
    reordered.splice(targetIndex, 0, moved);
    onVersionOrderChange(reordered.map((version) => version.slug));
  }

  function handleDragStart(event: DragEvent<HTMLDivElement>, slug: string) {
    setDraggedSlug(slug);
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", slug);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>, targetSlug: string) {
    event.preventDefault();
    const sourceSlug = draggedSlug ?? event.dataTransfer.getData("text/plain");
    if (sourceSlug) moveVersion(sourceSlug, targetSlug);
    setDraggedSlug(null);
    setDropTargetSlug(null);
  }

  function handleColumnKeyDown(
    event: KeyboardEvent<HTMLDivElement>,
    slug: string,
  ) {
    if (!event.altKey || (event.key !== "ArrowLeft" && event.key !== "ArrowRight")) {
      return;
    }
    event.preventDefault();
    const index = orderedVersions.findIndex((version) => version.slug === slug);
    const target = orderedVersions[index + (event.key === "ArrowLeft" ? -1 : 1)];
    if (target) moveVersion(slug, target.slug);
  }

  return (
    <div className="reader-paper" style={columnStyle}>
      <div className="reader-column-head">
        <span />
        {orderedVersions.map((version) => (
          <div
            className={cn(
              "reader-version-column min-w-0 px-6 py-4",
              draggedSlug === version.slug && "reader-version-column-dragging",
              dropTargetSlug === version.slug && "reader-version-column-target",
            )}
            draggable={Boolean(onVersionOrderChange)}
            key={version.id}
            tabIndex={onVersionOrderChange ? 0 : undefined}
            aria-label={`Move ${version.title} column`}
            title="Drag to reorder · Alt+Arrow keys also work"
            onDragStart={(event) => handleDragStart(event, version.slug)}
            onDragOver={(event) => {
              event.preventDefault();
              event.dataTransfer.dropEffect = "move";
              setDropTargetSlug(version.slug);
            }}
            onDragLeave={() => setDropTargetSlug(null)}
            onDrop={(event) => handleDrop(event, version.slug)}
            onDragEnd={() => {
              setDraggedSlug(null);
              setDropTargetSlug(null);
            }}
            onKeyDown={(event) => handleColumnKeyDown(event, version.slug)}
          >
            <div className="flex items-center gap-2">
              {onVersionOrderChange ? (
                <GripVertical className="version-drag-handle size-3.5" aria-hidden="true" />
              ) : null}
              <p className="truncate text-sm font-semibold">{version.title}</p>
              {version.roles.includes("default_source") ? (
                <Badge className="border-accent/30 bg-accent/8 text-accent">Source</Badge>
              ) : null}
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {version.language.native_name ?? version.language.name}
            </p>
          </div>
        ))}
      </div>

      <div>
        {reader.units.map((unit) => (
          <article className="reader-unit" id={unit.key} key={unit.id}>
            <div className="reader-unit-number" aria-label={`Unit ${unit.label}`}>
              {unit.label}
            </div>
            {orderedVersions.map((version) => {
              const segments = unit.segments[version.slug] ?? [];
              return (
                <div
                  className={cn(
                    "reader-cell",
                    version.language.script === "Grek" && "reader-cell-greek",
                  )}
                  dir={version.language.direction === "rtl" ? "rtl" : "ltr"}
                  lang={version.language.iso_code}
                  key={version.id}
                >
                  <div className="mobile-version-label">
                    <span>{version.abbreviation ?? version.title}</span>
                    <span>{version.language.name}</span>
                  </div>
                  {segments.length ? (
                    segments.map((segment) => (
                      <p
                        className={cn(
                          "reader-segment",
                          Boolean(segment.content_markup.paragraph_start) &&
                            "paragraph-start",
                        )}
                        key={segment.id}
                      >
                        <InterlinearSegment segment={segment} />
                        {segment.mapping_type !== "direct" ? (
                          <span className="mapping-note">{segment.mapping_type}</span>
                        ) : null}
                      </p>
                    ))
                  ) : (
                    <p className="reader-gap">No corresponding segment</p>
                  )}
                </div>
              );
            })}
          </article>
        ))}
      </div>
    </div>
  );
}
