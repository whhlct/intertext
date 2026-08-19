export interface TextSummary {
  id: string;
  slug: string;
  title: string;
  description: string | null;
}

export interface LanguageSummary {
  iso_code: string;
  name: string;
  native_name: string | null;
  script: string | null;
  direction: string;
}

export interface VersionSummary {
  id: string;
  slug: string;
  title: string;
  abbreviation: string | null;
  version_type: string;
  language: LanguageSummary;
  current_release_id: string | null;
}

export interface StructureNode {
  id: string;
  parent_id: string | null;
  node_type: string;
  title: string;
  short_title: string | null;
  ordinal: number;
  path: string | null;
  depth: number;
  start_unit_ordinal: number | null;
  end_unit_ordinal: number | null;
}

export interface CanonicalRangeEndpoint {
  id: string;
  key: string;
  ordinal: number;
}

export interface ReferenceResolution {
  text_slug: string;
  input: string;
  normalized_reference: string;
  label: string;
  reference_scheme: string;
  start: CanonicalRangeEndpoint;
  end: CanonicalRangeEndpoint;
}

export interface ReaderVersion {
  id: string;
  slug: string;
  title: string;
  abbreviation: string | null;
  language: LanguageSummary;
  roles: string[];
}

export interface ReaderSegment {
  id: string;
  sequence: number;
  text: string;
  content_markup: Record<string, unknown>;
  mapping_type: string;
}

export interface ReaderUnit {
  id: string;
  key: string;
  label: string;
  ordinal: number;
  segments: Record<string, ReaderSegment[]>;
}

export interface ReaderResponse {
  text: { id: string; slug: string; title: string };
  reference: { label: string; start: string; end: string };
  versions: ReaderVersion[];
  units: ReaderUnit[];
}
