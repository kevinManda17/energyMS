import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import KpiCard from "../components/KpiCard";

describe("KpiCard", () => {
  it("renders label, value and unit", () => {
    render(<KpiCard label="Production" value="3.4" unit="kW" />);
    expect(screen.getByText("Production")).toBeInTheDocument();
    expect(screen.getByText("3.4")).toBeInTheDocument();
    expect(screen.getByText("kW")).toBeInTheDocument();
  });
});
