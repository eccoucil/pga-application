import { render, screen } from "@/test-utils";
import userEvent from "@testing-library/user-event";
import { DeleteConfirmation } from "../DeleteConfirmation";
import type { Client } from "@/types/client";

const mockClient: Client = {
  id: "123",
  user_id: "user-1",
  name: "Acme Corp",
  company: "John Doe",
  email: "john@acme.com",
  phone: null,
  address: null,
  industry: "Technology",
  status: "active",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

describe("DeleteConfirmation", () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    onConfirm: jest.fn(),
    client: mockClient,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders nothing when isOpen is false", () => {
    const { container } = render(
      <DeleteConfirmation {...defaultProps} isOpen={false} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders nothing when client is null", () => {
    const { container } = render(
      <DeleteConfirmation {...defaultProps} client={null} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("displays the client name in the confirmation message", () => {
    render(<DeleteConfirmation {...defaultProps} />);
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("displays the Delete Client heading", () => {
    render(<DeleteConfirmation {...defaultProps} />);
    expect(
      screen.getByRole("heading", { name: "Delete Client" })
    ).toBeInTheDocument();
  });

  it("calls onClose when Cancel is clicked", async () => {
    const user = userEvent.setup();
    render(<DeleteConfirmation {...defaultProps} />);

    await user.click(screen.getByText("Cancel"));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onConfirm when Delete Client button is clicked", async () => {
    const user = userEvent.setup();
    render(<DeleteConfirmation {...defaultProps} />);

    const deleteButtons = screen.getAllByText("Delete Client");
    // The second "Delete Client" text is the action button (first is the heading)
    const actionButton = deleteButtons.find(
      (el) => el.tagName.toLowerCase() === "button"
    )!;
    await user.click(actionButton);

    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when X button is clicked", async () => {
    const user = userEvent.setup();
    render(<DeleteConfirmation {...defaultProps} />);

    // The X button is the first button in the header
    const buttons = screen.getAllByRole("button");
    // X close button is the first one (before Cancel and Delete)
    await user.click(buttons[0]);

    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });
});
