import { Button } from "@/components/ui/button";

export function Header() {
  return (
    <header className="flex items-center justify-between border-b border-zinc-800 pb-4">
      <div>
        <p className="text-sm text-zinc-400">Trading Intelligence</p>
        <h1 className="text-2xl font-semibold">Orca Trading Yuki</h1>
      </div>
      <Button variant="outline">Frontend Ready</Button>
    </header>
  );
}
