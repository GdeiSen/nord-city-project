/** Column configs for entity tables (users, tickets, feedbacks) */

export { serviceTicketColumns, serviceTicketColumnMeta } from "./service-tickets"
export { userColumns, userColumnMeta } from "./users"
export { feedbackColumns, feedbackColumnMeta } from "./feedbacks"
export { auditLogColumns, auditLogColumnMeta } from "./audit-log"
export type { TableColumnConfig, ColumnType } from "./types"
export { configToMeta } from "./types"
