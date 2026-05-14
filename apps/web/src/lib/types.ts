/** Shared client-side types. Mirror the API's Pydantic shapes. */

export type PostStatus = "draft" | "scheduled" | "published" | "archived";
export type UserRole = "reader" | "editor" | "admin";

export interface Me {
  id: string;
  email: string;
  role: UserRole;
  display_name: string;
}

export interface PostSummary {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  status: PostStatus;
  author_id: string;
  published_at: string | null;
  scheduled_for: string | null;
  updated_at: string;
  reading_time_minutes: number;
}

export interface PostDetail extends PostSummary {
  content_html: string;
  cover_image_id: string | null;
  category_id: string | null;
  series_id: string | null;
  series_order: number | null;
  meta_title: string | null;
  meta_description: string | null;
  canonical_url: string | null;
  robots: string | null;
  tag_ids: string[];
}

export interface PostList {
  items: PostSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface Tag {
  id: string;
  slug: string;
  name: string;
}

export interface SlugCheck {
  slug: string;
  available: boolean;
}

export interface TagRef { slug: string; name: string }
export interface CategoryRef { slug: string; name: string }
export interface SeriesRef { slug: string; title: string }
export interface AuthorOut { display_name: string; bio: string | null; avatar_url: string | null }

export interface MediaRef {
  cloud_name: string;
  cloudinary_public_id: string;
  width: number;
  height: number;
  alt: string;
  placeholder_data_url: string | null;
  focal_x: number | null;
  focal_y: number | null;
}

export interface PublicPostSummary {
  slug: string;
  title: string;
  excerpt: string | null;
  published_at: string;
  reading_time_minutes: number;
  cover: MediaRef | null;
  tags: TagRef[];
  author: AuthorOut;
}

export interface PublicPostDetail extends PublicPostSummary {
  content_html: string;
  updated_at: string;
  meta_title: string | null;
  meta_description: string | null;
  canonical_url: string | null;
  robots: string | null;
  category: CategoryRef | null;
  series: SeriesRef | null;
  series_order: number | null;
  comment_count: number;
  prev_in_series: PublicPostSummary | null;
  next_in_series: PublicPostSummary | null;
  related: PublicPostSummary[];
}

export interface PublicPostList {
  items: PublicPostSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface TagDetailOut {
  slug: string;
  name: string;
  posts: PublicPostList;
}

export interface CategoryDetailOut {
  slug: string;
  name: string;
  description: string | null;
  posts: PublicPostList;
}

export interface SeriesDetailOut {
  slug: string;
  title: string;
  description: string | null;
  posts: PublicPostSummary[];
}

export interface SearchResults {
  q: string;
  items: PublicPostSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface SitemapOut {
  posts: { slug: string; updated_at: string; published_at: string }[];
}

export interface SlugRedirectOut {
  entity_type: "post" | "tag" | "category" | "series";
  old_slug: string;
  new_slug: string;
}

export interface CommentPublic {
  id: string;
  parent_id: string | null;
  author_name: string;
  content: string;
  created_at: string;
}

export interface CommentAdmin extends CommentPublic {
  post_id: string;
  post_title: string;
  post_slug: string;
  status: "pending" | "approved" | "spam" | "deleted";
}

export interface CommentList {
  items: CommentAdmin[];
  total: number;
  limit: number;
  offset: number;
}

export interface SubscriberAdmin {
  id: string;
  email: string;
  status: "pending" | "confirmed" | "unsubscribed";
  confirmed_at: string | null;
  created_at: string;
}

export interface SubscriberList {
  items: SubscriberAdmin[];
  total: number;
  limit: number;
  offset: number;
}

export interface AnalyticsWindow {
  window: 7 | 30 | 90;
  top_posts: { slug: string; title: string; views: number }[];
  top_referrers: { host: string; views: number }[];
}
