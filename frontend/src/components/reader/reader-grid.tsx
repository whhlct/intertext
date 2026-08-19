import { Languages } from "lucide-react";
import type { CSSProperties } from "react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import type { ReaderResponse } from "@/types/api";

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

export function ReaderGrid({ reader }: { reader: ReaderResponse }) {
  const columnStyle = {
    "--reader-columns": Math.max(reader.versions.length, 1),
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

  return (
    <div className="reader-paper" style={columnStyle}>
      <div className="reader-column-head" aria-hidden="true">
        <span />
        {reader.versions.map((version) => (
          <div className="min-w-0 px-6 py-4" key={version.id}>
            <div className="flex items-center gap-2">
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
            {reader.versions.map((version) => {
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
                        {segment.text}
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
