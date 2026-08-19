"use client";

import { Check, Columns3 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { VersionSummary } from "@/types/api";

interface VersionPickerProps {
  versions: VersionSummary[];
  selected: string[];
  onToggle: (slug: string) => void;
}

export function VersionPicker({ versions, selected, onToggle }: VersionPickerProps) {
  const selectedOrder = new Map(selected.map((slug, index) => [slug, index]));
  const orderedVersions = versions.toSorted((left, right) => {
    const leftIndex = selectedOrder.get(left.slug);
    const rightIndex = selectedOrder.get(right.slug);
    if (leftIndex !== undefined && rightIndex !== undefined) {
      return leftIndex - rightIndex;
    }
    if (leftIndex !== undefined) return -1;
    if (rightIndex !== undefined) return 1;
    return left.title.localeCompare(right.title);
  });

  return (
    <details className="version-picker relative">
      <summary className="list-none">
        <Button asChild variant="outline" className="pointer-events-none min-w-36">
          <span>
            <Columns3 className="size-4" />
            {selected.length} {selected.length === 1 ? "version" : "versions"}
          </span>
        </Button>
      </summary>
      <div className="absolute right-0 z-40 mt-2 w-80 rounded-lg border border-border bg-popover p-2 shadow-xl">
        <div className="px-2 pt-2 pb-1">
          <p className="text-xs font-semibold tracking-[0.13em] text-muted-foreground uppercase">
            Compare editions
          </p>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            Choose the columns shown in the aligned reader.
          </p>
        </div>
        <div className="mt-2 space-y-1">
          {orderedVersions.map((version) => {
            const active = selected.includes(version.slug);
            const isLast = active && selected.length === 1;
            return (
              <button
                type="button"
                key={version.id}
                disabled={isLast}
                onClick={() => onToggle(version.slug)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md px-2 py-2.5 text-left transition-colors hover:bg-muted disabled:cursor-not-allowed disabled:opacity-70",
                  active && "bg-muted/70",
                )}
              >
                <span
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded border",
                    active
                      ? "border-primary bg-primary text-primary-foreground"
                      : "border-border bg-background",
                  )}
                >
                  {active ? <Check className="size-3.5" /> : null}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium">
                    {version.title}
                  </span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">
                    {version.language.name}
                  </span>
                </span>
                {version.abbreviation ? <Badge>{version.abbreviation}</Badge> : null}
              </button>
            );
          })}
        </div>
      </div>
    </details>
  );
}
