"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAppStore } from "@/lib/store";
import Sidebar from "@/components/Sidebar";
import WorkspaceMain from "@/components/WorkspaceMain";
import PainelIA from "@/components/PainelIA";

export default function WorkspacePage() {
  const router = useRouter();
  const token = useAppStore((s) => s.token);

  useEffect(() => {
    if (!token) router.replace("/");
  }, [token, router]);

  if (!token) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-gray-950">
      {/* Coluna esquerda: sidebar com demandas */}
      <Sidebar />

      {/* Centro: workspace da demanda ativa */}
      <main className="flex-1 flex flex-col overflow-hidden border-x border-gray-800">
        <WorkspaceMain />
      </main>

      {/* Direita: painel IA (chat + progresso + citações) */}
      <PainelIA />
    </div>
  );
}
