"use client";

import { BookOpenText, ChevronRight, Library, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { StructureNode, TextSummary } from "@/types/api";

interface ReferenceSidebarProps {
  open: boolean;
  texts: TextSummary[];
  textSlug: string;
  books: StructureNode[];
  chapters: StructureNode[];
  selectedBookId: string;
  currentReference: string;
  onClose: () => void;
  onTextChange: (slug: string) => void;
  onBookChange: (node: StructureNode) => void;
  onChapterChange: (node: StructureNode) => void;
}

export function ReferenceSidebar({
  open,
  texts,
  textSlug,
  books,
  chapters,
  selectedBookId,
  currentReference,
  onClose,
  onTextChange,
  onBookChange,
  onChapterChange,
}: ReferenceSidebarProps) {
  return (
    <>
      <button
        type="button"
        aria-label="Close navigation"
        onClick={onClose}
        className={cn(
          "fixed inset-0 z-40 bg-foreground/30 backdrop-blur-[2px] transition-opacity lg:hidden",
          open ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      />
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-[min(88vw,23rem)] flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform duration-300 lg:static lg:z-auto lg:w-80 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <div className="flex h-20 items-center justify-between border-b border-sidebar-border px-5">
          <div className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-full border border-sidebar-ring/40 bg-sidebar-primary font-serif text-lg text-sidebar-primary-foreground">
              I
            </span>
            <div>
              <p className="font-serif text-xl leading-none tracking-tight">Intertext</p>
              <p className="mt-1 text-[0.64rem] font-semibold tracking-[0.18em] text-sidebar-foreground/55 uppercase">
                Comparative reader
              </p>
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="lg:hidden"
            aria-label="Close navigation"
          >
            <X className="size-4" />
          </Button>
        </div>

        <div className="border-b border-sidebar-border p-4">
          <label className="mb-2 flex items-center gap-2 text-[0.67rem] font-semibold tracking-[0.14em] text-sidebar-foreground/55 uppercase">
            <Library className="size-3.5" /> Corpus
          </label>
          <select
            value={textSlug}
            onChange={(event) => onTextChange(event.target.value)}
            className="h-10 w-full rounded-md border border-sidebar-border bg-sidebar-accent px-3 text-sm font-medium outline-none focus:ring-2 focus:ring-sidebar-ring"
          >
            {texts.map((text) => (
              <option key={text.id} value={text.slug}>
                {text.title}
              </option>
            ))}
          </select>
        </div>

        <div className="grid min-h-0 flex-1 grid-cols-[1fr_5.25rem]">
          <div className="min-h-0 overflow-y-auto border-r border-sidebar-border px-2 py-3">
            <p className="px-3 pb-2 text-[0.67rem] font-semibold tracking-[0.14em] text-sidebar-foreground/50 uppercase">
              {books[0]?.node_type === "book" ? "Books" : "Sections"}
            </p>
            <nav aria-label="Text structure" className="space-y-0.5">
              {books.map((book) => {
                const selected = book.id === selectedBookId;
                return (
                  <button
                    type="button"
                    key={book.id}
                    onClick={() => onBookChange(book)}
                    className={cn(
                      "group flex w-full items-center justify-between rounded-md px-3 py-2 text-left text-sm transition-colors",
                      selected
                        ? "bg-sidebar-primary text-sidebar-primary-foreground"
                        : "text-sidebar-foreground/78 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                    )}
                  >
                    <span className="truncate">{book.title}</span>
                    <ChevronRight
                      className={cn(
                        "size-3.5 opacity-0 transition-opacity group-hover:opacity-60",
                        selected && "opacity-70",
                      )}
                    />
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="min-h-0 overflow-y-auto py-3">
            <p className="px-2 pb-2 text-center text-[0.62rem] font-semibold tracking-[0.12em] text-sidebar-foreground/50 uppercase">
              Ch.
            </p>
            <nav aria-label="Subsections" className="grid grid-cols-2 gap-1 px-2">
              {chapters.map((chapter) => {
                const selected =
                  currentReference === chapter.title ||
                  currentReference.startsWith(`${chapter.title}:`);
                return (
                  <button
                    type="button"
                    key={chapter.id}
                    title={chapter.title}
                    onClick={() => onChapterChange(chapter)}
                    className={cn(
                      "flex aspect-square items-center justify-center rounded-md text-xs tabular-nums transition-colors",
                      selected
                        ? "bg-sidebar-primary text-sidebar-primary-foreground"
                        : "text-sidebar-foreground/65 hover:bg-sidebar-accent hover:text-sidebar-foreground",
                    )}
                  >
                    {chapter.short_title ?? chapter.ordinal}
                  </button>
                );
              })}
            </nav>
          </div>
        </div>

        <div className="border-t border-sidebar-border px-5 py-4 text-xs leading-5 text-sidebar-foreground/55">
          <div className="flex items-center gap-2 font-medium text-sidebar-foreground/75">
            <BookOpenText className="size-3.5" /> Canonical alignment
          </div>
          <p className="mt-1">References stay synchronized across every selected edition.</p>
        </div>
      </aside>
    </>
  );
}
