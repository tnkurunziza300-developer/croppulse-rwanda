import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { AgriculturalDataPage } from './AgriculturalDataPage';

vi.mock('./api', () => ({
  getNisrStatistics: vi.fn().mockResolvedValue({
    publisher: 'National Institute of Statistics of Rwanda (NISR)', title: 'SAS crop tables',
    source_url: 'https://statistics.gov.rw/test', reference_period: '2025 Seasons A/B/C',
    retrieved_at: '2026-10-21', units: 'area ha; production tonnes', limitations: 'Aggregate district data.',
    quality_report: {}, coverage: { n_valid: 30, missing_districts: [], coverage_label: 'Rwanda-wide dataset (all 30 districts present)' },
    available_years: [2025], available_seasons: ['A', 'B'], available_districts: ['Huye', 'Karongi'],
    available_crops: ['Maize', 'Beans'],
    records: [
      { district: 'Huye', crop: 'Maize', season: 'A', year: 2025, area_ha: 100, production_t: 200, yield_t_ha: 2 },
      { district: 'Karongi', crop: 'Beans', season: 'B', year: 2025, area_ha: 50, production_t: 40, yield_t_ha: 0.8 },
    ],
  }),
}));

describe('AgriculturalDataPage', () => {
  it('loads NISR provenance and filters district records', async () => {
    render(<AgriculturalDataPage />);
    expect(await screen.findByText('National Institute of Statistics of Rwanda (NISR)')).toBeInTheDocument();
    expect(screen.getAllByText('Huye').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Karongi').length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText('District'), { target: { value: 'Huye' } });
    await waitFor(() => expect(screen.getByRole('table').querySelector('tbody')?.textContent).not.toContain('Karongi'));
    expect(screen.getByText('200 t')).toBeInTheDocument();
  });
});
