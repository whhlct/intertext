import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "./page";

describe("Home", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.replaceState(null, "", "/");
  });

  it("renders the comparative reader shell while the library loads", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => undefined)));
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>,
    );

    expect(screen.getAllByText("Intertext")).not.toHaveLength(0);
    expect(screen.getByRole("heading", { name: "Choose a passage" })).toBeInTheDocument();
    expect(screen.getByText("Canonical alignment")).toBeInTheDocument();
  });

  it("loads navigation and an aligned passage from the API", async () => {
    const jsonResponse = (body: unknown) =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      });
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url === "/api/v1/texts") {
        return jsonResponse([
          { id: "bible", slug: "bible", title: "Bible", description: null },
        ]);
      }
      if (url.endsWith("/versions")) {
        return jsonResponse([
          {
            id: "kjv",
            slug: "kjv",
            title: "King James Version",
            abbreviation: "KJV",
            version_type: "translation",
            language: {
              iso_code: "en",
              name: "English",
              native_name: "English",
              script: "Latn",
              direction: "ltr",
            },
            current_release_id: "release-kjv",
          },
          {
            id: "sblgnt",
            slug: "sblgnt",
            title: "SBL Greek New Testament",
            abbreviation: "SBLGNT",
            version_type: "critical_edition",
            language: {
              iso_code: "grc",
              name: "Ancient Greek",
              native_name: "Ἑλληνική",
              script: "Grek",
              direction: "ltr",
            },
            current_release_id: "release-sblgnt",
          },
        ]);
      }
      if (url.endsWith("/structure")) {
        return jsonResponse([
          {
            id: "mark",
            parent_id: null,
            node_type: "book",
            title: "Mark",
            short_title: "Mark",
            ordinal: 41,
            path: "bible.mark",
            depth: 0,
            start_unit_ordinal: 1,
            end_unit_ordinal: 1,
          },
        ]);
      }
      if (url.includes("/structure/mark/children")) {
        return jsonResponse([
          {
            id: "mark-1",
            parent_id: "mark",
            node_type: "chapter",
            title: "Mark 1",
            short_title: "1",
            ordinal: 1,
            path: "bible.mark.1",
            depth: 1,
            start_unit_ordinal: 1,
            end_unit_ordinal: 1,
          },
        ]);
      }
      if (url.includes("/references/resolve")) {
        return jsonResponse({
          text_slug: "bible",
          input: "Mark 1",
          normalized_reference: "mark 1",
          label: "Mark 1",
          reference_scheme: "Intertext Bible",
          start: { id: "unit", key: "bible.mark.1.1", ordinal: 1 },
          end: { id: "unit", key: "bible.mark.1.1", ordinal: 1 },
        });
      }
      if (url.includes("/api/v1/reader/")) {
        return jsonResponse({
          text: { id: "bible", slug: "bible", title: "Bible" },
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
                    id: "segment",
                    sequence: 1,
                    text: "The beginning of the gospel",
                    content_markup: {},
                    mapping_type: "direct",
                  },
                ],
              },
            },
          ],
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "Mark 1" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("The beginning of the gospel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark" })).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([url]) =>
        String(url).includes("versions=kjv%2Csblgnt"),
      ),
    ).toBe(true);
  });

  it("reads a top-level leaf section without requiring child chapters", async () => {
    const jsonResponse = (body: unknown) =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve(body),
      });
    const fetchMock = vi.fn((input: string | URL | Request) => {
      const url = String(input);
      if (url === "/api/v1/texts") {
        return jsonResponse([
          { id: "quran", slug: "quran", title: "Quran", description: null },
        ]);
      }
      if (url.endsWith("/versions")) {
        return jsonResponse([
          {
            id: "tanzil",
            slug: "tanzil-simple",
            title: "Tanzil Quran Text (Simple)",
            abbreviation: "Tanzil Simple",
            version_type: "digital_edition",
            language: {
              iso_code: "ar",
              name: "Arabic",
              native_name: "العربية",
              script: "Arab",
              direction: "rtl",
            },
            current_release_id: "release-tanzil",
          },
        ]);
      }
      if (url.endsWith("/structure")) {
        return jsonResponse([
          {
            id: "al-fatihah",
            parent_id: null,
            node_type: "surah",
            title: "الفاتحة",
            short_title: "1",
            ordinal: 1,
            path: "quran.1",
            depth: 0,
            start_unit_ordinal: 1001,
            end_unit_ordinal: 1007,
          },
        ]);
      }
      if (url.includes("/structure/al-fatihah/children")) {
        return jsonResponse([]);
      }
      if (url.includes("/references/resolve")) {
        return jsonResponse({
          text_slug: "quran",
          input: "الفاتحة",
          normalized_reference: "الفاتحة",
          label: "الفاتحة",
          reference_scheme: "Intertext Quran",
          start: { id: "ayah", key: "quran.1.1", ordinal: 1001 },
          end: { id: "ayah", key: "quran.1.7", ordinal: 1007 },
        });
      }
      if (url.includes("/api/v1/reader/")) {
        return jsonResponse({
          text: { id: "quran", slug: "quran", title: "Quran" },
          reference: {
            label: "الفاتحة",
            start: "quran.1.1",
            end: "quran.1.7",
          },
          versions: [
            {
              id: "tanzil",
              slug: "tanzil-simple",
              title: "Tanzil Quran Text (Simple)",
              abbreviation: "Tanzil Simple",
              language: {
                iso_code: "ar",
                name: "Arabic",
                native_name: "العربية",
                script: "Arab",
                direction: "rtl",
              },
              roles: ["default_source"],
            },
          ],
          units: [
            {
              id: "ayah",
              key: "quran.1.1",
              label: "1",
              ordinal: 1001,
              segments: {
                "tanzil-simple": [
                  {
                    id: "segment",
                    sequence: 1,
                    text: "بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ",
                    content_markup: {},
                    mapping_type: "direct",
                  },
                ],
              },
            },
          ],
        });
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <Home />
      </QueryClientProvider>,
    );

    expect(
      await screen.findByRole("heading", { name: "الفاتحة" }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText("بِسْمِ اللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ"),
    ).toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Subsections" })).toBeNull();
  });
});
