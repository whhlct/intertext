import { fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import { VersionPicker } from "@/components/reader/version-picker";
import type { ReaderResponse } from "@/types/api";

import { ReaderGrid } from "./reader-grid";

const reader: ReaderResponse = {
  text: { id: "text", slug: "bible", title: "Bible" },
  reference: {
    label: "Mark 1",
    start: "bible.mark.1.1",
    end: "bible.mark.1.1",
  },
  versions: [
    {
      id: "sblgnt",
      slug: "sblgnt",
      title: "SBL Greek New Testament",
      abbreviation: "SBLGNT",
      language: {
        iso_code: "grc",
        name: "Ancient Greek",
        native_name: "Ἑλληνική",
        script: "Grek",
        direction: "ltr",
      },
      roles: ["default_source"],
    },
    {
      id: "kjv",
      slug: "kjv",
      title: "King James Version",
      abbreviation: "KJV",
      language: {
        iso_code: "en",
        name: "English",
        native_name: "English",
        script: "Latn",
        direction: "ltr",
      },
      roles: [],
    },
  ],
  units: [
    {
      id: "unit",
      key: "bible.mark.1.1",
      label: "1",
      ordinal: 1,
      segments: {
        sblgnt: [
          {
            id: "greek-segment",
            sequence: 1,
            text: "Ἀρχὴ τοῦ ⸀εὐαγγελίου.",
            content_markup: {},
            mapping_type: "direct",
            tokens: [
              {
                id: "token-1",
                index: 0,
                surface: "Ἀρχὴ",
                normalized: "αρχη",
                char_start: 0,
                char_end: 4,
                glosses: [
                  {
                    gloss: "[The] beginning",
                    gloss_type: "contextual",
                    source: "TAGNT",
                    language: {
                      iso_code: "en",
                      name: "English",
                      native_name: "English",
                      script: "Latn",
                      direction: "ltr",
                    },
                  },
                ],
              },
              {
                id: "token-2",
                index: 1,
                surface: "τοῦ",
                normalized: "του",
                char_start: 5,
                char_end: 8,
                glosses: [
                  {
                    gloss: "of the",
                    gloss_type: "contextual",
                    source: "TAGNT",
                    language: {
                      iso_code: "en",
                      name: "English",
                      native_name: "English",
                      script: "Latn",
                      direction: "ltr",
                    },
                  },
                ],
              },
              {
                id: "token-3",
                index: 2,
                surface: "εὐαγγελίου",
                normalized: "ευαγγελιου",
                char_start: 10,
                char_end: 20,
                glosses: [
                  {
                    gloss: "gospel",
                    gloss_type: "contextual",
                    source: "TAGNT",
                    language: {
                      iso_code: "en",
                      name: "English",
                      native_name: "English",
                      script: "Latn",
                      direction: "ltr",
                    },
                  },
                ],
              },
            ],
          },
        ],
        kjv: [
          {
            id: "english-segment",
            sequence: 1,
            text: "The beginning of the gospel",
            content_markup: {},
            mapping_type: "direct",
          },
        ],
      },
    },
  ],
};

describe("ReaderGrid", () => {
  it("renders aligned versions and canonical text units", () => {
    render(<ReaderGrid reader={reader} versionOrder={["kjv", "sblgnt"]} />);

    const englishHeading = screen.getByText("King James Version");
    const sourceHeading = screen.getByText("SBL Greek New Testament");
    expect(
      englishHeading.compareDocumentPosition(sourceHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByText("Ἀρχὴ")).toBeInTheDocument();
    expect(screen.getByText("⸀εὐαγγελίου.")).toBeInTheDocument();
    expect(screen.getByText("[The] beginning")).toBeInTheDocument();
    expect(screen.getByText("of the")).toBeInTheDocument();
    expect(screen.getByText("gospel")).toBeInTheDocument();
    expect(screen.getByText("The beginning of the gospel")).toBeInTheDocument();
    expect(screen.getByLabelText("Unit 1")).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
  });

  it("keeps dragged column order synchronized with the version picker", () => {
    const reorderableReader = reader;
    const pickerVersions = reorderableReader.versions.map((version) => ({
      ...version,
      version_type: "translation",
      current_release_id: `${version.id}-release`,
    }));

    function Harness() {
      const [order, setOrder] = useState(["kjv", "sblgnt"]);
      return (
        <>
          <VersionPicker
            versions={pickerVersions}
            selected={order}
            onToggle={() => undefined}
          />
          <ReaderGrid
            reader={reorderableReader}
            versionOrder={order}
            onVersionOrderChange={setOrder}
          />
        </>
      );
    }

    const { container } = render(<Harness />);
    const transferred = new Map<string, string>();
    const dataTransfer = {
      effectAllowed: "move",
      dropEffect: "move",
      setData: (type: string, value: string) => transferred.set(type, value),
      getData: (type: string) => transferred.get(type) ?? "",
    };
    const harness = within(container);
    const sourceColumn = harness.getByLabelText(
      "Move SBL Greek New Testament column",
    );
    const targetColumn = harness.getByLabelText("Move King James Version column");

    fireEvent.dragStart(sourceColumn, { dataTransfer });
    fireEvent.dragOver(targetColumn, { dataTransfer });
    fireEvent.drop(targetColumn, { dataTransfer });

    const pickerItems = [...container.querySelectorAll(".version-picker button")];
    expect(pickerItems.map((item) => item.textContent)).toEqual([
      expect.stringContaining("SBL Greek New Testament"),
      expect.stringContaining("King James Version"),
    ]);
    expect(
      sourceColumn.compareDocumentPosition(targetColumn) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
