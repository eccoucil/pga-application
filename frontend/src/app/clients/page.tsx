import { DashboardLayout } from "@/components/layout/DashboardLayout"
import { ClientManagement } from "@/components/clients/ClientManagement"

export default function ClientsPage() {
  return (
    <DashboardLayout>
      <ClientManagement />
    </DashboardLayout>
  )
}
