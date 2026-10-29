import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, type FarmTimelineEntry } from './api';
import { FarmTimeline } from './FarmTimeline';

vi.mock('./api', () => ({ api: vi.fn() }));
const mockedApi = vi.mocked(api);

afterEach(() => vi.clearAllMocks());
beforeEach(() => vi.resetAllMocks());

function entry(overrides: Partial<FarmTimelineEntry> & Pick<FarmTimelineEntry, 'id' | 'event_type' | 'event_date' | 'description'>): FarmTimelineEntry {
  return {
    farm_id: 'farm-1', farm_name: 'Home farm', field_id: null, field_name: null,
    source_label: 'Farmer reported', href: '#harvest-records-title', ...overrides,
  };
}

describe('farmer farm activity timeline', () => {
  it('shows multiple existing record types in chronological order with source labels and original-record links', async () => {
    mockedApi.mockResolvedValue({ entries: [
      entry({ id: 'no-date', event_type: 'activity', event_date: null, description: 'Older undated record' }),
      entry({ id: 'harvest', event_type: 'harvest', event_date: '2025-11-01', field_id: 'field-1', field_name: 'East field', description: 'Harvest recorded for Beans: 12 kg.' }),
      entry({ id: 'soil', event_type: 'soil_test', event_date: '2025-10-01', description: 'Soil-test values entered; no measurements recorded.', source_label: 'Farmer entered; source not independently verified', href: '#soil-records-title' }),
    ], has_more: false });

    render(<FarmTimeline farmId="farm-1" />);
    const harvest = await screen.findByText('Harvest recorded for Beans: 12 kg.');
    const soil = screen.getByText('Soil-test values entered; no measurements recorded.');
    const undated = screen.getByText('Older undated record');
    expect(harvest.compareDocumentPosition(soil) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(soil.compareDocumentPosition(undated) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/Home farm · East field/, { selector: '.timeline-context' })).toBeInTheDocument();
    expect(screen.getByText('Farmer entered; source not independently verified')).toBeInTheDocument();
    expect(screen.getByText('Date not recorded')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'View harvest records' })).toHaveAttribute('href', '#harvest-records-title');
    expect(screen.getByRole('link', { name: 'View soil records' })).toHaveAttribute('href', '#soil-records-title');
    expect(mockedApi).toHaveBeenCalledWith('/v1/farms/farm-1/timeline');
  });

  it('shows loading and explains an empty timeline without implying that no work occurred', async () => {
    let resolve!: (value: { entries: FarmTimelineEntry[]; has_more: boolean }) => void;
    mockedApi.mockReturnValue(new Promise((done) => { resolve = done; }));
    render(<FarmTimeline farmId="farm-1" />);
    expect(screen.getByRole('status')).toHaveTextContent('Loading farm timeline');
    resolve({ entries: [], has_more: false });
    expect(await screen.findByText(/This does not show whether other farm activity occurred/)).toBeInTheDocument();
  });

  it('displays API errors and keeps a retry action', async () => {
    mockedApi.mockRejectedValueOnce(new Error('Timeline service unavailable.'))
      .mockResolvedValueOnce({ entries: [], has_more: false });
    render(<FarmTimeline farmId="farm-1" />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Timeline service unavailable.');
    screen.getByRole('button', { name: 'Try again' }).click();
    expect(await screen.findByText(/No existing records are available/)).toBeInTheDocument();
  });
});
