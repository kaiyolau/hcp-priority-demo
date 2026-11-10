import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DOCTORS } from '../test/fixtures';
import { PriorityTable } from './PriorityTable';

function rowNames() {
  return screen.getAllByRole('row').slice(1).map((r) => within(r).getAllByRole('cell')[1].textContent);
}

describe('PriorityTable', () => {
  it('renders HCPs in rank order with colour-coded scores', () => {
    render(<PriorityTable doctors={DOCTORS} selectedId="hcp-001" onSelect={() => {}} />);
    expect(rowNames()).toEqual(['Dr. Test OneVancouver', 'Dr. Test TwoToronto', 'Dr. Test ThreeCalgary']);
    expect(screen.getByLabelText('Score 78 of 100, high priority')).toHaveAttribute('data-tier', 'high');
    expect(screen.getByLabelText('Score 12 of 100, low priority')).toHaveAttribute('data-tier', 'low');
  });

  it('calls onSelect when a row is clicked or chosen with the keyboard', async () => {
    const onSelect = vi.fn();
    const user = userEvent.setup();
    render(<PriorityTable doctors={DOCTORS} selectedId="hcp-001" onSelect={onSelect} />);

    await user.click(screen.getByText('Dr. Test Two'));
    expect(onSelect).toHaveBeenLastCalledWith('hcp-002', { reveal: true });

    screen.getByTestId('row-hcp-001').focus();
    await user.keyboard('{ArrowDown}');
    expect(onSelect).toHaveBeenLastCalledWith('hcp-002');
  });

  it('filters by search text and specialty', async () => {
    const user = userEvent.setup();
    render(<PriorityTable doctors={DOCTORS} selectedId={null} onSelect={() => {}} />);

    await user.type(screen.getByPlaceholderText('Search name or city'), 'toronto');
    expect(rowNames()).toEqual(['Dr. Test TwoToronto']);

    await user.clear(screen.getByPlaceholderText('Search name or city'));
    await user.selectOptions(screen.getByLabelText('Filter by specialty'), 'Neurology');
    expect(rowNames()).toEqual(['Dr. Test ThreeCalgary']);
  });

  it('sorts by a column and exposes aria-sort', async () => {
    const user = userEvent.setup();
    render(<PriorityTable doctors={DOCTORS} selectedId={null} onSelect={() => {}} />);
    const header = screen.getByRole('button', { name: /HCP/ });
    await user.click(header);
    expect(rowNames()).toEqual(['Dr. Test OneVancouver', 'Dr. Test ThreeCalgary', 'Dr. Test TwoToronto']);
    expect(screen.getByRole('columnheader', { name: /HCP/ })).toHaveAttribute('aria-sort', 'ascending');

    await user.click(header);
    expect(rowNames()[0]).toBe('Dr. Test TwoToronto');
    expect(screen.getByRole('columnheader', { name: /HCP/ })).toHaveAttribute('aria-sort', 'descending');
  });
});
