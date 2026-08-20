import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

describe("shadcn/ui primitives", () => {
  it("renders Badge variants", () => {
    render(<Badge variant="amber">ALERT</Badge>);
    expect(screen.getByText("ALERT")).toBeInTheDocument();
  });

  it("renders Button with touch size (gloved)", () => {
    render(<Button size="touch">ACK</Button>);
    const btn = screen.getByText("ACK");
    expect(btn.className).toContain("h-14");
  });

  it("renders Card with title", () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Operator — Voice-first</CardTitle>
        </CardHeader>
        <CardContent>85 dB · gloved</CardContent>
      </Card>
    );
    expect(screen.getByText(/Operator/)).toBeInTheDocument();
    expect(screen.getByText(/85 dB/)).toBeInTheDocument();
  });
});
