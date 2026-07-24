"use client";

import { ImpersonationStartForm } from "@/components/admin/ImpersonationStartForm";
import { Modal } from "@/components/ui";
import type { UserPublic } from "@/lib/types/lifecycle";

export type ImpersonationStartModalProps = {
  open: boolean;
  onClose: () => void;
  target: UserPublic;
};

export function ImpersonationStartModal({
  open,
  onClose,
  target,
}: ImpersonationStartModalProps) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Impersonate user"
      description="Start an audited session to view Pàdéyá as this account."
      className="sm:max-w-xl"
    >
      <ImpersonationStartForm
        userId={target.id}
        target={target}
        onCancel={onClose}
        onStarted={onClose}
      />
    </Modal>
  );
}
