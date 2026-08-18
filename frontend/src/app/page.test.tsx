import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Home from "./page";

describe("Home", () => {
  it("introduces Intertext", () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: "Read texts in conversation." })).toBeInTheDocument();
  });
});

