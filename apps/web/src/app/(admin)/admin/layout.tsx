import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { Sidebar } from "@/components/admin/sidebar";
import { Topbar } from "@/components/admin/topbar";
import { DialogHost } from "@/components/ui/dialog-host";
import { ApiError, apiFetch } from "@/lib/api";
import type { Me } from "@/lib/types";

export default async function AdminLayout({ children }: { children: ReactNode }) {
  let me: Me;
  try {
    const { data } = await apiFetch<Me>("/v1/auth/me");
    me = data;
  } catch (err) {
    if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
      redirect("/admin/login");
    }
    throw err;
  }

  return (
    <div className="flex min-h-dvh bg-bg text-fg">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar me={me} />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
      <DialogHost />
    </div>
  );
}
