/**
 * TypeScript type definitions for the Service Management System
 *
 * These types are based on the Python ORM models and provide type safety
 * for the frontend application communicating with the backend service.
 */

// Role constants and types
export const USER_ROLES = {
  GUEST: 0,
  USER_LPR: 10011,
  USER_MA: 20122,
  ADMIN: 10012,
  SUPER_ADMIN: 10013,
} as const

export type UserRole = typeof USER_ROLES[keyof typeof USER_ROLES]

export const ROLE_LABELS: Record<UserRole, string> = {
  [USER_ROLES.GUEST]: 'Guest',
  [USER_ROLES.USER_LPR]: 'User LPR',
  [USER_ROLES.USER_MA]: 'User MA',
  [USER_ROLES.ADMIN]: 'Administrator',
  [USER_ROLES.SUPER_ADMIN]: 'Super Admin',
} as const

export const ROLE_BADGE_VARIANTS: Record<UserRole, 'destructive' | 'default' | 'secondary' | 'outline'> = {
  [USER_ROLES.GUEST]: 'outline',
  [USER_ROLES.USER_LPR]: 'default',
  [USER_ROLES.USER_MA]: 'secondary',
  [USER_ROLES.ADMIN]: 'destructive',
  [USER_ROLES.SUPER_ADMIN]: 'destructive',
} as const

// Service ticket statuses and priorities
export const TICKET_STATUS = {
  NEW: 'NEW',
  ACCEPTED: 'ACCEPTED',
  ASSIGNED: 'ASSIGNED',
  COMPLETED: 'COMPLETED',
} as const

export type TicketStatus = typeof TICKET_STATUS[keyof typeof TICKET_STATUS]

export const TICKET_STATUS_LABELS_RU: Record<TicketStatus, string> = {
  [TICKET_STATUS.NEW]: 'Новая',
  [TICKET_STATUS.ACCEPTED]: 'Принята',
  [TICKET_STATUS.ASSIGNED]: 'В работе',
  [TICKET_STATUS.COMPLETED]: 'Завершена',
} as const

export const TICKET_STATUS_FILTER_LABELS_RU: Record<TicketStatus, string> = {
  [TICKET_STATUS.NEW]: 'Новые',
  [TICKET_STATUS.ACCEPTED]: 'Принятые',
  [TICKET_STATUS.ASSIGNED]: 'В работе',
  [TICKET_STATUS.COMPLETED]: 'Завершенные',
} as const

export const TICKET_PRIORITY = {
  LOW: 1,
  MEDIUM: 2,
  HIGH: 3,
  CRITICAL: 4,
} as const

export type TicketPriority = typeof TICKET_PRIORITY[keyof typeof TICKET_PRIORITY]

export const TICKET_PRIORITY_LABELS_RU: Record<TicketPriority, string> = {
  [TICKET_PRIORITY.LOW]: 'Низкий',
  [TICKET_PRIORITY.MEDIUM]: 'Средний',
  [TICKET_PRIORITY.HIGH]: 'Высокий',
  [TICKET_PRIORITY.CRITICAL]: 'Критический',
} as const

/**
 * Base interface for entities with timestamps
 */
export interface BaseEntity {
  id: number;
  created_at: string;
  updated_at: string;
}

/**
 * User entity representing system users (from Telegram)
 * 
 * @interface User
 * @extends BaseEntity
 */
export interface User extends BaseEntity {
  /** Telegram user ID (BigInteger) */
  id: number;
  /** Telegram username without @ symbol */
  username?: string;
  /** User role identifier for permissions */
  role?: number;
  /** User's first name from Telegram profile */
  first_name?: string;
  /** User's last name from Telegram profile */
  last_name?: string;
  /** Additional middle name field */
  middle_name?: string;
  /** User's language preference, defaults to 'ru' */
  language_code: string;
  /** GDPR consent flag */
  data_processing_consent: boolean;
  /** Associated object/location ID */
  object_id?: number;
  /** Associated legal entity information */
  legal_entity?: string;
  /** Contact phone number */
  phone_number?: string;
  /** Contact email address */
  email?: string;
  /** Associated rental object */
  object?: RentalObject;
}

/**
 * Rental object entity representing business centers/buildings
 * 
 * @interface RentalObject
 * @extends BaseEntity
 */
export interface RentalObject extends BaseEntity {
  /** Object name */
  name: string;
  /** Object address */
  address: string;
  /** Object description */
  description?: string;
  /** Array of photo URLs */
  photos: string[];
  /** Rental object status (ACTIVE, INACTIVE, etc.) */
  status: string;
  /** Associated spaces/offices */
  spaces?: RentalSpace[];
  /** Users associated with this object */
  users?: User[];
}

/**
 * Rental space entity representing office spaces for rent
 * 
 * @interface RentalSpace
 * @extends BaseEntity
 */
export interface RentalSpace extends BaseEntity {
  /** Associated object ID */
  object_id: number;
  /** Floor information */
  floor: string;
  /** Space size in square meters */
  size: number;
  /** Space description */
  description?: string;
  /** Array of photo URLs */
  photos: string[];
  /** Space status (FREE, OCCUPIED, etc.) */
  status: string;
  /** Associated object */
  object?: RentalObject;
  /** Space views */
  views?: RentalSpaceView[];
}

/**
 * Rental space view entity for tracking space views
 * 
 * @interface RentalSpaceView
 * @extends BaseEntity
 */
export interface RentalSpaceView extends BaseEntity {
  /** Space ID being viewed */
  space_id: number;
  /** User ID who viewed the space */
  user_id: number;
  /** Associated space */
  space?: RentalSpace;
  /** User who viewed */
  user?: User;
  /** View timestamp */
  viewed_at: string;
}

/**
 * Service ticket entity for maintenance requests
 * 
 * @interface ServiceTicket
 * @extends BaseEntity
 */
export interface ServiceTicket extends BaseEntity {
  /** User ID who created the ticket */
  user_id: number;
  /** Ticket description */
  description?: string;
  /** Location where service is needed */
  location?: string;
  /** Image URL for the ticket */
  image?: string;
  /** Ticket status (NEW, ACCEPTED, ASSIGNED, COMPLETED) */
  status: TicketStatus;
  /** Dialog ID format: 0000-0000-0000 */
  ddid?: string;
  /** Answer/response text */
  answer?: string;
  /** Additional details */
  details?: string;
  /** Ticket priority (1-4) */
  priority: TicketPriority;
  /** Ticket category */
  category?: string;
  /** Associated user */
  user?: User;
  /** Associated rental object (from user's object_id) */
  object?: { id: number; name: string };
  /** Status history logs */
  status_logs?: ServiceTicketLog[];
}

/**
 * Service ticket log entry for tracking status changes
 * 
 * @interface ServiceTicketLog
 * @extends BaseEntity
 */
export interface ServiceTicketLog extends BaseEntity {
  /** Service ticket ID */
  ticket_id: number;
  /** Status value (NEW, ACCEPTED, ASSIGNED, COMPLETED) */
  status: string;
  /** User ID who changed the status */
  user_id?: number;
  /** Assignee name or identifier */
  assignee?: string;
  /** Telegram message ID for tracking */
  message_id?: number;
  /** Comment about the status change */
  comment?: string;
  /** Associated service ticket */
  ticket?: ServiceTicket;
  /** User who made the change */
  user?: User;
}

// Keep the old interface name for backward compatibility
export interface ServiceTicketStatus extends ServiceTicketLog {}

/**
 * Feedback entity for user feedback
 * 
 * @interface Feedback
 * @extends BaseEntity
 */
export interface Feedback extends BaseEntity {
  /** User ID who provided feedback */
  user_id: number;
  /** Dialog ID format: 0000-0000-0000 */
  ddid: string;
  /** Feedback answer/response */
  answer: string;
  /** Additional feedback text */
  text?: string;
  /** Associated user */
  user?: User;
}

/**
 * Poll answer entity for survey responses
 * 
 * @interface PollAnswer
 * @extends BaseEntity
 */
export interface PollAnswer extends BaseEntity {
  /** User ID who answered */
  user_id: number;
  /** Dialog ID format: 0000-0000-0000 */
  ddid: string;
  /** Answer value */
  answer: string;
  /** Additional metadata */
  meta?: string;
  /** Associated user */
  user?: User;
}

/**
 * API Response wrapper for backend communication
 * 
 * @interface ApiResponse
 */
export interface ApiResponse<T = any> {
  /** Success status */
  success: boolean;
  /** Response data */
  data?: T;
  /** Error message if failed */
  message?: string;
  /** Error details */
  error?: any;
}

/**
 * Pagination interface for list responses
 * 
 * @interface Pagination
 */
export interface Pagination {
  /** Current page number */
  page: number;
  /** Items per page */
  limit: number;
  /** Total number of items */
  total: number;
  /** Total number of pages */
  pages: number;
}

/**
 * Paginated response wrapper
 * 
 * @interface PaginatedResponse
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  /** Pagination information */
  pagination: Pagination;
}

/**
 * Dashboard statistics interface
 * 
 * @interface DashboardStats
 */
export interface DashboardStats {
  /** Total number of users */
  total_users: number;
  /** Total number of service tickets */
  total_tickets: number;
  /** Number of pending tickets */
  pending_tickets: number;
  /** Number of completed tickets */
  completed_tickets: number;
  /** Total number of feedbacks */
  total_feedbacks: number;
  /** Total number of objects */
  total_objects: number;
  /** Total number of spaces */
  total_spaces: number;
  /** Number of available spaces */
  available_spaces: number;
}

/**
 * Service ticket statistics interface
 * 
 * @interface TicketStats
 */
export interface TicketStats {
  /** Tickets by status */
  by_status: Record<number, number>;
  /** Tickets by priority */
  by_priority: Record<number, number>;
  /** Tickets by category */
  by_category: Record<string, number>;
  /** Monthly ticket counts */
  monthly_counts: Array<{
    month: string;
    count: number;
  }>;
}

/**
 * Filter options for data queries
 * 
 * @interface FilterOptions
 */
export interface FilterOptions {
  /** Search query */
  search?: string;
  /** Status filter */
  status?: number;
  /** Priority filter */
  priority?: number;
  /** Category filter */
  category?: string;
  /** Date range filter */
  date_from?: string;
  date_to?: string;
  /** Object ID filter */
  object_id?: number;
}

/**
 * Sort options for data queries
 * 
 * @interface SortOptions
 */
export interface SortOptions {
  /** Field to sort by */
  field: string;
  /** Sort order */
  order: 'asc' | 'desc';
}

/**
 * Query parameters for API requests
 * 
 * @interface QueryParams
 */
export interface QueryParams {
  /** Page number */
  page?: number;
  /** Items per page */
  limit?: number;
  /** Filter options */
  filters?: FilterOptions;
  /** Sort options */
  sort?: SortOptions;
}

/**
 * Menu item interface for navigation
 * 
 * @interface MenuItem
 */
export interface MenuItem {
  /** Menu item title */
  title: string;
  /** Menu item URL */
  url: string;
  /** Menu item icon */
  icon?: React.ComponentType<any>;
  /** Whether the item is active */
  isActive?: boolean;
  /** Submenu items */
  items?: MenuItem[];
} 