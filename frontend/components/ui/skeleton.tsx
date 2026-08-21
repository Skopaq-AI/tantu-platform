import { cn } from "@/lib/utils";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-md bg-slate-200 dark:bg-slate-800", className)} {...props} />;
}

export function CardSkeleton() {
  return (
    <div className="rounded-xl border bg-white dark:bg-slate-900 p-5 space-y-3">
      <Skeleton className="h-4 w-1/3" />
      <Skeleton className="h-3 w-2/3" />
      <Skeleton className="h-24 w-full" />
      <div className="flex gap-2">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-24" />
      </div>
    </div>
  );
}

export function ChartSkeleton() {
  return (
    <div className="h-[200px] w-full flex flex-col gap-2">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="flex-1 w-full" />
      <div className="flex justify-between">
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}

export function FleetGridSkeleton() {
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="border rounded-xl p-4 space-y-2 bg-white dark:bg-slate-900">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-4 w-48" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-12 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}
