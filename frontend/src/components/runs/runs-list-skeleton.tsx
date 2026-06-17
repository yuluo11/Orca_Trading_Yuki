import { Card, CardContent } from "@/components/ui/card";

export function RunsListSkeleton() {
  // Generate 4 placeholder cards
  const skeletons = Array.from({ length: 4 }).map((_, i) => i);

  return (
    <div className="space-y-4">
      {skeletons.map((i) => (
        <Card key={i} className="border-zinc-800 bg-zinc-900/50 animate-pulse">
          <CardContent className="p-4 flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Icon placeholder */}
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-zinc-800/80" />
              <div>
                <div className="flex items-center gap-3 mb-2">
                  {/* Symbol placeholder */}
                  <div className="h-5 w-16 bg-zinc-800/80 rounded" />
                  {/* Badge placeholder */}
                  <div className="h-5 w-20 bg-zinc-800/80 rounded" />
                </div>
                {/* Meta details placeholder */}
                <div className="h-4 w-48 bg-zinc-800/80 rounded" />
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-right hidden sm:block">
                {/* Decision title placeholder */}
                <div className="h-3 w-12 bg-zinc-800/80 rounded mb-2 ml-auto" />
                {/* Decision badge placeholder */}
                <div className="h-6 w-16 bg-zinc-800/80 rounded ml-auto" />
              </div>
              {/* Chevron placeholder */}
              <div className="w-5 h-5 bg-zinc-800/80 rounded" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
