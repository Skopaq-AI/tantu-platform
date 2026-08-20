import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2", {
  variants: {
    variant: {
      default: "border-transparent bg-slate-900 text-white",
      secondary: "border-transparent bg-slate-100 text-slate-900",
      outline: "text-slate-700 border-slate-200",
      sky: "border-sky-200 bg-sky-100 text-sky-800",
      amber: "border-amber-200 bg-amber-100 text-amber-800",
      emerald: "border-emerald-200 bg-emerald-100 text-emerald-800",
      violet: "border-violet-200 bg-violet-100 text-violet-800",
      red: "border-red-200 bg-red-100 text-red-800",
    },
  },
  defaultVariants: { variant: "default" },
});

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
