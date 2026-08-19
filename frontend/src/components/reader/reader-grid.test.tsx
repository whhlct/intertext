import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

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
            text: "Ἀρχὴ τοῦ εὐαγγελίου",
            content_markup: {},
            mapping_type: "direct",
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
    render(<ReaderGrid reader={reader} />);

    expect(screen.getAllByText("SBL Greek New Testament")).not.toHaveLength(0);
    expect(screen.getByText("Ἀρχὴ τοῦ εὐαγγελίου")).toBeInTheDocument();
    expect(screen.getByText("The beginning of the gospel")).toBeInTheDocument();
    expect(screen.getByLabelText("Unit 1")).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
  });
});
