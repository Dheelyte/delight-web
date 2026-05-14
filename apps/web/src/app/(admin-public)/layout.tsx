import type { ReactNode } from "react";

import { DialogHost } from "@/components/ui/dialog-host";

export default function AdminPublicLayout({ children }: { children: ReactNode }) {
  return (
    <>
      {children}
      <DialogHost />
    </>
  );
}
