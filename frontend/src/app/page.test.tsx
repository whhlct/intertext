import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import Home from "./page";

describe("Home", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
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
});
