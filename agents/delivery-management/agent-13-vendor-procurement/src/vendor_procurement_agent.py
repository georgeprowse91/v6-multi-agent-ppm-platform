"""
Agent 13: Vendor & Procurement Management Agent

Purpose:
Streamlines end-to-end procurement lifecycle from vendor onboarding and contract management
to purchase order processing and invoice reconciliation. Ensures external spending aligns
with organizational policies and supports vendor performance monitoring.

Specification: agents/delivery-management/agent-13-vendor-procurement/README.md
"""

from datetime import datetime
from typing import Any

from agents.runtime import BaseAgent


class VendorProcurementAgent(BaseAgent):
    """
    Vendor & Procurement Management Agent - Manages procurement lifecycle and vendor relationships.

    Key Capabilities:
    - Vendor registry and onboarding
    - Procurement request intake and processing
    - RFP/RFQ generation and quote management
    - Vendor selection and scoring
    - Contract and agreement management
    - Purchase order creation and approval
    - Invoice receipt and reconciliation
    - Vendor performance monitoring
    - Compliance and audit support
    """

    def __init__(self, agent_id: str = "agent_013", config: dict[str, Any] | None = None):
        super().__init__(agent_id, config)

        # Configuration parameters
        self.default_currency = config.get("default_currency", "USD") if config else "USD"
        self.procurement_threshold = config.get("procurement_threshold", 10000) if config else 10000
        self.min_vendor_proposals = config.get("min_vendor_proposals", 3) if config else 3
        self.invoice_tolerance_pct = config.get("invoice_tolerance_pct", 0.05) if config else 0.05

        # Vendor categories
        self.vendor_categories = (
            config.get(
                "vendor_categories",
                ["software", "hardware", "consulting", "materials", "services", "cloud"],
            )
            if config
            else ["software", "hardware", "consulting", "materials", "services", "cloud"]
        )

        # Data stores (will be replaced with database)
        self.vendors: dict[str, Any] = {}
        self.procurement_requests: dict[str, Any] = {}
        self.rfps: dict[str, Any] = {}
        self.proposals: dict[str, Any] = {}
        self.contracts: dict[str, Any] = {}
        self.purchase_orders: dict[str, Any] = {}
        self.invoices: dict[str, Any] = {}
        self.vendor_performance: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize database connections, ERP integrations, and AI models."""
        await super().initialize()
        self.logger.info("Initializing Vendor & Procurement Management Agent...")

        # TODO: Initialize Azure SQL Database or Cosmos DB for vendor registry
        # TODO: Connect to procurement systems (SAP Ariba, Coupa, Oracle Procurement, Dynamics)
        # TODO: Set up Azure Blob Storage for contract documents and RFP responses
        # TODO: Initialize Azure Machine Learning for vendor recommendation models
        # TODO: Connect to ERP & Accounts Payable systems
        # TODO: Set up Azure Form Recognizer for contract clause extraction
        # TODO: Initialize integration with DocuSign/Adobe Sign for e-signatures
        # TODO: Connect to third-party risk databases (Dun & Bradstreet)
        # TODO: Set up Azure Service Bus for procurement event publishing
        # TODO: Initialize Azure Key Vault for storing vendor credentials

        self.logger.info("Vendor & Procurement Management Agent initialized")

    async def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input data based on the requested action."""
        action = input_data.get("action", "")

        if not action:
            self.logger.warning("No action specified")
            return False

        valid_actions = [
            "onboard_vendor",
            "create_procurement_request",
            "generate_rfp",
            "submit_proposal",
            "evaluate_proposals",
            "select_vendor",
            "create_contract",
            "create_purchase_order",
            "submit_invoice",
            "reconcile_invoice",
            "track_vendor_performance",
            "get_vendor_scorecard",
            "search_vendors",
            "get_procurement_status",
        ]

        if action not in valid_actions:
            self.logger.warning(f"Invalid action: {action}")
            return False

        if action == "onboard_vendor":
            vendor_data = input_data.get("vendor", {})
            required_fields = ["legal_name", "contact_email", "category"]
            for field in required_fields:
                if field not in vendor_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        elif action == "create_procurement_request":
            request_data = input_data.get("request", {})
            required_fields = ["requester", "description", "estimated_cost"]
            for field in required_fields:
                if field not in request_data:
                    self.logger.warning(f"Missing required field: {field}")
                    return False

        return True

    async def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process vendor and procurement management requests.

        Args:
            input_data: {
                "action": "onboard_vendor" | "create_procurement_request" | "generate_rfp" |
                          "submit_proposal" | "evaluate_proposals" | "select_vendor" |
                          "create_contract" | "create_purchase_order" | "submit_invoice" |
                          "reconcile_invoice" | "track_vendor_performance" | "get_vendor_scorecard" |
                          "search_vendors" | "get_procurement_status",
                "vendor": Vendor data for onboarding/updates,
                "request": Procurement request data,
                "rfp": RFP details,
                "proposal": Vendor proposal data,
                "contract": Contract details,
                "purchase_order": PO data,
                "invoice": Invoice information,
                "vendor_id": Vendor identifier,
                "request_id": Procurement request ID,
                "criteria": Search/evaluation criteria,
                "filters": Query filters
            }

        Returns:
            Response based on action:
            - onboard_vendor: Vendor ID and onboarding status
            - create_procurement_request: Request ID and workflow status
            - generate_rfp: RFP ID and invitation details
            - submit_proposal: Proposal ID and submission confirmation
            - evaluate_proposals: Evaluation results and vendor rankings
            - select_vendor: Selection confirmation and next steps
            - create_contract: Contract ID and terms summary
            - create_purchase_order: PO number and approval status
            - submit_invoice: Invoice ID and receipt confirmation
            - reconcile_invoice: Reconciliation status and payment details
            - track_vendor_performance: Performance metrics and trends
            - get_vendor_scorecard: Comprehensive vendor scorecard
            - search_vendors: List of matching vendors
            - get_procurement_status: Procurement request status details
        """
        action = input_data.get("action", "search_vendors")

        if action == "onboard_vendor":
            return await self._onboard_vendor(input_data.get("vendor", {}))

        elif action == "create_procurement_request":
            return await self._create_procurement_request(input_data.get("request", {}))

        elif action == "generate_rfp":
            return await self._generate_rfp(input_data.get("request_id"), input_data.get("rfp", {}))  # type: ignore

        elif action == "submit_proposal":
            return await self._submit_proposal(
                input_data.get("rfp_id"),  # type: ignore
                input_data.get("vendor_id"),  # type: ignore
                input_data.get("proposal", {}),
            )

        elif action == "evaluate_proposals":
            return await self._evaluate_proposals(
                input_data.get("rfp_id"), input_data.get("criteria", {})  # type: ignore
            )

        elif action == "select_vendor":
            return await self._select_vendor(input_data.get("rfp_id"), input_data.get("vendor_id"))  # type: ignore

        elif action == "create_contract":
            return await self._create_contract(input_data.get("contract", {}))

        elif action == "create_purchase_order":
            return await self._create_purchase_order(input_data.get("purchase_order", {}))

        elif action == "submit_invoice":
            return await self._submit_invoice(input_data.get("invoice", {}))

        elif action == "reconcile_invoice":
            return await self._reconcile_invoice(input_data.get("invoice_id"))  # type: ignore

        elif action == "track_vendor_performance":
            return await self._track_vendor_performance(input_data.get("vendor_id"))  # type: ignore

        elif action == "get_vendor_scorecard":
            return await self._get_vendor_scorecard(input_data.get("vendor_id"))  # type: ignore

        elif action == "search_vendors":
            return await self._search_vendors(input_data.get("criteria", {}))

        elif action == "get_procurement_status":
            return await self._get_procurement_status(input_data.get("request_id"))  # type: ignore

        else:
            raise ValueError(f"Unknown action: {action}")

    async def _onboard_vendor(self, vendor_data: dict[str, Any]) -> dict[str, Any]:
        """
        Onboard a new vendor with compliance checks.

        Returns vendor ID and onboarding status.
        """
        self.logger.info(f"Onboarding vendor: {vendor_data.get('legal_name')}")

        # Generate vendor ID
        vendor_id = await self._generate_vendor_id()

        # Run compliance checks
        compliance_checks = await self._run_compliance_checks(vendor_data)

        # Calculate initial risk score
        risk_score = await self._calculate_vendor_risk(vendor_data, compliance_checks)

        # Create vendor profile
        vendor = {
            "vendor_id": vendor_id,
            "legal_name": vendor_data.get("legal_name"),
            "tax_id": vendor_data.get("tax_id"),
            "contact_email": vendor_data.get("contact_email"),
            "contact_phone": vendor_data.get("contact_phone"),
            "address": vendor_data.get("address", {}),
            "category": vendor_data.get("category"),
            "certifications": vendor_data.get("certifications", []),
            "diversity_classification": vendor_data.get("diversity_classification"),
            "risk_score": risk_score,
            "compliance_checks": compliance_checks,
            "status": "Pending Approval",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": vendor_data.get("requester", "unknown"),
            "performance_metrics": {
                "total_contracts": 0,
                "total_spend": 0,
                "on_time_delivery_rate": 0,
                "quality_rating": 0,
                "compliance_rating": 0,
            },
        }

        # Store vendor
        self.vendors[vendor_id] = vendor

        # TODO: Store in database
        # TODO: Submit for approval via Approval Workflow Agent
        # TODO: Publish vendor.onboarded event

        return {
            "vendor_id": vendor_id,
            "status": "Pending Approval",
            "legal_name": vendor["legal_name"],
            "risk_score": risk_score,
            "compliance_checks": compliance_checks,
            "next_steps": "Vendor pending approval. Submit required documentation.",
        }

    async def _create_procurement_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new procurement request.

        Returns request ID and workflow status.
        """
        self.logger.info(f"Creating procurement request: {request_data.get('description')}")

        # Generate request ID
        request_id = await self._generate_request_id()

        # Categorize request
        category = await self._categorize_procurement_request(request_data)

        # Check budget availability
        budget_check = await self._check_budget_availability(request_data)

        # Suggest preferred vendors
        suggested_vendors = await self._suggest_vendors(category, request_data)

        # Determine approval path
        approval_path = await self._determine_approval_path(request_data.get("estimated_cost", 0))

        # Create procurement request
        request = {
            "request_id": request_id,
            "requester": request_data.get("requester"),
            "project_id": request_data.get("project_id"),
            "program_id": request_data.get("program_id"),
            "description": request_data.get("description"),
            "quantity": request_data.get("quantity", 1),
            "estimated_cost": request_data.get("estimated_cost"),
            "currency": request_data.get("currency", self.default_currency),
            "required_date": request_data.get("required_date"),
            "justification": request_data.get("justification"),
            "category": category,
            "suggested_vendors": suggested_vendors,
            "budget_available": budget_check.get("available", False),
            "approval_path": approval_path,
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store request
        self.procurement_requests[request_id] = request

        # TODO: Store in database
        # TODO: Route to approval workflow if estimated_cost > threshold

        return {
            "request_id": request_id,
            "status": "Draft",
            "category": category,
            "estimated_cost": request["estimated_cost"],
            "budget_available": budget_check.get("available", False),
            "suggested_vendors": suggested_vendors,
            "approval_required": request_data.get("estimated_cost", 0) > self.procurement_threshold,
            "next_steps": "Review suggested vendors or generate RFP",
        }

    async def _generate_rfp(self, request_id: str, rfp_data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate RFP from procurement request.

        Returns RFP ID and invitation details.
        """
        self.logger.info(f"Generating RFP for request: {request_id}")

        request = self.procurement_requests.get(request_id)
        if not request:
            raise ValueError(f"Procurement request not found: {request_id}")

        # Generate RFP ID
        rfp_id = await self._generate_rfp_id()

        # Select RFP template based on category
        template = await self._select_rfp_template(request.get("category"))

        # Generate RFP content
        rfp_content = await self._generate_rfp_content(request, template, rfp_data)

        # Select vendors to invite
        invited_vendors = await self._select_vendors_to_invite(
            request.get("category"),
            request.get("suggested_vendors", []),
            rfp_data.get("vendor_ids", []),
        )

        # Create RFP
        rfp = {
            "rfp_id": rfp_id,
            "request_id": request_id,
            "title": rfp_data.get("title", request.get("description")),
            "content": rfp_content,
            "requirements": rfp_data.get("requirements", []),
            "evaluation_criteria": rfp_data.get("evaluation_criteria", {}),
            "submission_deadline": rfp_data.get("submission_deadline"),
            "invited_vendors": invited_vendors,
            "proposals_received": [],
            "status": "Published",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store RFP
        self.rfps[rfp_id] = rfp

        # TODO: Store in database and blob storage
        # TODO: Send RFP invitations via email
        # TODO: Publish rfp.published event

        return {
            "rfp_id": rfp_id,
            "request_id": request_id,
            "title": rfp["title"],
            "submission_deadline": rfp["submission_deadline"],
            "invited_vendors": len(invited_vendors),
            "vendor_list": invited_vendors,
            "next_steps": "Wait for vendor proposals by submission deadline",
        }

    async def _submit_proposal(
        self, rfp_id: str, vendor_id: str, proposal_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Submit vendor proposal for RFP.

        Returns proposal ID and submission confirmation.
        """
        self.logger.info(f"Submitting proposal from vendor {vendor_id} for RFP {rfp_id}")

        rfp = self.rfps.get(rfp_id)
        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id}")

        # Generate proposal ID
        proposal_id = await self._generate_proposal_id()

        # Validate submission deadline
        deadline = datetime.fromisoformat(rfp.get("submission_deadline"))
        if datetime.utcnow() > deadline:
            raise ValueError("Submission deadline has passed")

        # Create proposal
        proposal = {
            "proposal_id": proposal_id,
            "rfp_id": rfp_id,
            "vendor_id": vendor_id,
            "pricing": proposal_data.get("pricing", {}),
            "delivery_schedule": proposal_data.get("delivery_schedule"),
            "terms": proposal_data.get("terms", {}),
            "technical_response": proposal_data.get("technical_response"),
            "attachments": proposal_data.get("attachments", []),
            "evaluation_score": None,  # Calculated during evaluation
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "Submitted",
        }

        # Store proposal
        self.proposals[proposal_id] = proposal

        # Update RFP
        rfp["proposals_received"].append(proposal_id)

        # TODO: Store in database and blob storage
        # TODO: Publish proposal.submitted event

        return {
            "proposal_id": proposal_id,
            "rfp_id": rfp_id,
            "vendor_id": vendor_id,
            "submitted_at": proposal["submitted_at"],
            "status": "Submitted",
            "next_steps": "Proposal will be evaluated after submission deadline",
        }

    async def _evaluate_proposals(self, rfp_id: str, criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate all proposals for an RFP.

        Returns evaluation results and vendor rankings.
        """
        self.logger.info(f"Evaluating proposals for RFP: {rfp_id}")

        rfp = self.rfps.get(rfp_id)
        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id}")

        proposal_ids = rfp.get("proposals_received", [])
        if len(proposal_ids) < self.min_vendor_proposals:
            self.logger.warning(
                f"Only {len(proposal_ids)} proposals received, minimum is {self.min_vendor_proposals}"
            )

        # Get evaluation criteria with weights
        eval_criteria = criteria or rfp.get(
            "evaluation_criteria",
            {"cost": 0.40, "quality": 0.30, "delivery": 0.15, "risk": 0.10, "diversity": 0.05},
        )

        # Evaluate each proposal
        evaluated_proposals = []
        for proposal_id in proposal_ids:
            proposal = self.proposals.get(proposal_id)
            if not proposal:
                continue

            # Calculate scores for each criterion
            scores = await self._score_proposal(proposal, eval_criteria)

            # Calculate weighted total score
            total_score = sum(
                scores.get(criterion, 0) * weight for criterion, weight in eval_criteria.items()
            )

            # Update proposal with evaluation
            proposal["evaluation_score"] = total_score
            proposal["criterion_scores"] = scores

            evaluated_proposals.append(
                {
                    "proposal_id": proposal_id,
                    "vendor_id": proposal.get("vendor_id"),
                    "total_score": total_score,
                    "scores": scores,
                    "pricing": proposal.get("pricing"),
                }
            )

        # Rank proposals by score
        ranked_proposals = sorted(evaluated_proposals, key=lambda x: x["total_score"], reverse=True)

        # TODO: Store evaluation results in database
        # TODO: Use Azure ML for AI-based vendor recommendation

        return {
            "rfp_id": rfp_id,
            "proposals_evaluated": len(evaluated_proposals),
            "evaluation_criteria": eval_criteria,
            "rankings": ranked_proposals,
            "recommended_vendor": ranked_proposals[0] if ranked_proposals else None,
            "evaluation_date": datetime.utcnow().isoformat(),
        }

    async def _select_vendor(self, rfp_id: str, vendor_id: str) -> dict[str, Any]:
        """
        Select vendor and finalize procurement.

        Returns selection confirmation and next steps.
        """
        self.logger.info(f"Selecting vendor {vendor_id} for RFP {rfp_id}")

        rfp = self.rfps.get(rfp_id)
        if not rfp:
            raise ValueError(f"RFP not found: {rfp_id}")

        # Find selected proposal
        selected_proposal = None
        for proposal_id in rfp.get("proposals_received", []):
            proposal = self.proposals.get(proposal_id)
            if proposal and proposal.get("vendor_id") == vendor_id:
                selected_proposal = proposal
                break

        if not selected_proposal:
            raise ValueError(f"No proposal found from vendor {vendor_id}")

        # Document selection rationale
        # TODO: Use Azure OpenAI for generating selection rationale

        # Update RFP and proposal status
        rfp["status"] = "Vendor Selected"
        rfp["selected_vendor_id"] = vendor_id
        rfp["selected_proposal_id"] = selected_proposal.get("proposal_id")
        selected_proposal["status"] = "Accepted"

        # TODO: Store in database
        # TODO: Notify all vendors of selection decision
        # TODO: Publish vendor.selected event

        return {
            "rfp_id": rfp_id,
            "selected_vendor_id": vendor_id,
            "proposal_id": selected_proposal.get("proposal_id"),
            "pricing": selected_proposal.get("pricing"),
            "evaluation_score": selected_proposal.get("evaluation_score"),
            "next_steps": "Generate contract from approved templates",
        }

    async def _create_contract(self, contract_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create contract from template.

        Returns contract ID and terms summary.
        """
        self.logger.info(f"Creating contract with vendor: {contract_data.get('vendor_id')}")

        # Generate contract ID
        contract_id = await self._generate_contract_id()

        # Select contract template
        await self._select_contract_template(contract_data.get("type", "standard"))

        # Extract key clauses
        # TODO: Use Azure Form Recognizer for clause extraction
        key_clauses = await self._extract_contract_clauses(contract_data)

        # Create contract
        contract = {
            "contract_id": contract_id,
            "vendor_id": contract_data.get("vendor_id"),
            "project_id": contract_data.get("project_id"),
            "type": contract_data.get("type", "standard"),
            "start_date": contract_data.get("start_date"),
            "end_date": contract_data.get("end_date"),
            "value": contract_data.get("value"),
            "currency": contract_data.get("currency", self.default_currency),
            "terms": contract_data.get("terms", {}),
            "obligations": contract_data.get("obligations", []),
            "slas": contract_data.get("slas", []),
            "renewal_options": contract_data.get("renewal_options"),
            "key_clauses": key_clauses,
            "attachments": contract_data.get("attachments", []),
            "status": "Draft",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store contract
        self.contracts[contract_id] = contract

        # TODO: Store in database and document repository
        # TODO: Route for e-signature via DocuSign/Adobe Sign
        # TODO: Publish contract.created event

        return {
            "contract_id": contract_id,
            "vendor_id": contract["vendor_id"],
            "type": contract["type"],
            "value": contract["value"],
            "start_date": contract["start_date"],
            "end_date": contract["end_date"],
            "status": "Draft",
            "next_steps": "Review contract and submit for approval and signatures",
        }

    async def _create_purchase_order(self, po_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create purchase order from approved procurement.

        Returns PO number and approval status.
        """
        self.logger.info(f"Creating purchase order for vendor: {po_data.get('vendor_id')}")

        # Generate PO number
        po_number = await self._generate_po_number()

        # Create PO
        purchase_order = {
            "po_number": po_number,
            "vendor_id": po_data.get("vendor_id"),
            "contract_id": po_data.get("contract_id"),
            "project_id": po_data.get("project_id"),
            "items": po_data.get("items", []),
            "total_value": await self._calculate_po_total(po_data.get("items", [])),
            "currency": po_data.get("currency", self.default_currency),
            "delivery_schedule": po_data.get("delivery_schedule"),
            "delivery_address": po_data.get("delivery_address"),
            "payment_terms": po_data.get("payment_terms"),
            "approval_history": [],
            "status": "Pending Approval",
            "created_at": datetime.utcnow().isoformat(),
        }

        # Store PO
        self.purchase_orders[po_number] = purchase_order

        # TODO: Store in database
        # TODO: Route for approval via Approval Workflow Agent
        # TODO: Release to vendor upon approval

        return {
            "po_number": po_number,
            "vendor_id": purchase_order["vendor_id"],
            "total_value": purchase_order["total_value"],
            "status": "Pending Approval",
            "items_count": len(purchase_order["items"]),
            "next_steps": "Submit for approval. Will be released to vendor upon approval.",
        }

    async def _submit_invoice(self, invoice_data: dict[str, Any]) -> dict[str, Any]:
        """
        Submit vendor invoice.

        Returns invoice ID and receipt confirmation.
        """
        self.logger.info(f"Submitting invoice: {invoice_data.get('invoice_number')}")

        # Generate internal invoice ID
        invoice_id = await self._generate_invoice_id()

        # Create invoice record
        invoice = {
            "invoice_id": invoice_id,
            "vendor_invoice_number": invoice_data.get("invoice_number"),
            "vendor_id": invoice_data.get("vendor_id"),
            "po_number": invoice_data.get("po_number"),
            "invoice_date": invoice_data.get("invoice_date"),
            "due_date": invoice_data.get("due_date"),
            "line_items": invoice_data.get("line_items", []),
            "subtotal": invoice_data.get("subtotal"),
            "tax": invoice_data.get("tax"),
            "total_amount": invoice_data.get("total_amount"),
            "currency": invoice_data.get("currency", self.default_currency),
            "payment_terms": invoice_data.get("payment_terms"),
            "attachments": invoice_data.get("attachments", []),
            "reconciliation_status": "Pending",
            "payment_status": "Unpaid",
            "received_at": datetime.utcnow().isoformat(),
        }

        # Store invoice
        self.invoices[invoice_id] = invoice

        # TODO: Store in database
        # TODO: Initiate automatic reconciliation
        # TODO: Publish invoice.received event

        return {
            "invoice_id": invoice_id,
            "vendor_invoice_number": invoice["vendor_invoice_number"],
            "po_number": invoice["po_number"],
            "total_amount": invoice["total_amount"],
            "reconciliation_status": "Pending",
            "next_steps": "Invoice will be automatically reconciled against PO and receipts",
        }

    async def _reconcile_invoice(self, invoice_id: str) -> dict[str, Any]:
        """
        Reconcile invoice against PO and receipts (three-way matching).

        Returns reconciliation status and payment details.
        """
        self.logger.info(f"Reconciling invoice: {invoice_id}")

        invoice = self.invoices.get(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")

        # Get associated PO
        po_number = invoice.get("po_number")
        purchase_order = self.purchase_orders.get(po_number)
        if not purchase_order:
            raise ValueError(f"Purchase order not found: {po_number}")

        # Perform three-way matching
        matching_result = await self._three_way_match(invoice, purchase_order)

        # Check for discrepancies
        discrepancies = matching_result.get("discrepancies", [])

        if not discrepancies:
            # No discrepancies - approve for payment
            invoice["reconciliation_status"] = "Matched"
            invoice["approved_for_payment"] = True
            invoice["approved_at"] = datetime.utcnow().isoformat()

            # TODO: Initiate payment in ERP
            payment_status = await self._initiate_payment(invoice)

            invoice["payment_status"] = payment_status.get("status", "Processing")
            invoice["payment_reference"] = payment_status.get("reference")

        else:
            # Discrepancies found - flag for review
            invoice["reconciliation_status"] = "Discrepancy"
            invoice["approved_for_payment"] = False
            invoice["discrepancies"] = discrepancies

        # TODO: Store in database
        # TODO: Publish invoice.reconciled event

        return {
            "invoice_id": invoice_id,
            "reconciliation_status": invoice["reconciliation_status"],
            "discrepancies": discrepancies,
            "approved_for_payment": invoice.get("approved_for_payment", False),
            "payment_status": invoice.get("payment_status"),
            "payment_reference": invoice.get("payment_reference"),
            "next_steps": (
                "Payment initiated" if not discrepancies else "Review and resolve discrepancies"
            ),
        }

    async def _track_vendor_performance(self, vendor_id: str) -> dict[str, Any]:
        """
        Track vendor performance metrics.

        Returns performance data and trends.
        """
        self.logger.info(f"Tracking performance for vendor: {vendor_id}")

        vendor = self.vendors.get(vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")

        # Collect performance data
        performance_data = await self._collect_vendor_performance_data(vendor_id)

        # Calculate metrics
        metrics = {
            "delivery_timeliness": await self._calculate_delivery_timeliness(vendor_id),
            "quality_rating": await self._calculate_quality_rating(vendor_id),
            "compliance_score": await self._calculate_compliance_score(vendor_id),
            "sla_adherence": await self._calculate_sla_adherence(vendor_id),
            "dispute_count": performance_data.get("dispute_count", 0),
            "total_spend": performance_data.get("total_spend", 0),
            "contract_count": performance_data.get("contract_count", 0),
        }

        # Update vendor performance metrics
        vendor["performance_metrics"].update(metrics)

        # TODO: Store in database
        # TODO: Publish vendor.performance_updated event

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.get("legal_name"),
            "metrics": metrics,
            "performance_trend": await self._analyze_performance_trend(vendor_id),
            "recommendations": await self._generate_vendor_recommendations(metrics),
        }

    async def _get_vendor_scorecard(self, vendor_id: str) -> dict[str, Any]:
        """
        Generate comprehensive vendor scorecard.

        Returns detailed scorecard with visualizations.
        """
        self.logger.info(f"Generating scorecard for vendor: {vendor_id}")

        vendor = self.vendors.get(vendor_id)
        if not vendor:
            raise ValueError(f"Vendor not found: {vendor_id}")

        # Get performance metrics
        performance = await self._track_vendor_performance(vendor_id)

        # Get contract history
        contracts = await self._get_vendor_contracts(vendor_id)

        # Get recent issues
        recent_issues = await self._get_vendor_issues(vendor_id)

        # Calculate overall score
        overall_score = await self._calculate_overall_vendor_score(vendor)

        return {
            "vendor_id": vendor_id,
            "vendor_name": vendor.get("legal_name"),
            "overall_score": overall_score,
            "risk_score": vendor.get("risk_score"),
            "performance_metrics": performance.get("metrics"),
            "performance_trend": performance.get("performance_trend"),
            "contract_summary": {
                "active_contracts": len([c for c in contracts if c.get("status") == "Active"]),
                "total_value": sum(c.get("value", 0) for c in contracts),
                "expiring_soon": len([c for c in contracts if await self._is_expiring_soon(c)]),
            },
            "recent_issues": recent_issues,
            "recommendations": performance.get("recommendations"),
            "generated_at": datetime.utcnow().isoformat(),
        }

    async def _search_vendors(self, criteria: dict[str, Any]) -> dict[str, Any]:
        """
        Search vendors by criteria.

        Returns list of matching vendors.
        """
        self.logger.info("Searching vendors")

        # Filter vendors
        matching_vendors = []
        for vendor_id, vendor in self.vendors.items():
            if await self._matches_criteria(vendor, criteria):
                matching_vendors.append(
                    {
                        "vendor_id": vendor_id,
                        "legal_name": vendor.get("legal_name"),
                        "category": vendor.get("category"),
                        "risk_score": vendor.get("risk_score"),
                        "performance_rating": vendor.get("performance_metrics", {}).get(
                            "quality_rating", 0
                        ),
                        "status": vendor.get("status"),
                    }
                )

        # Sort by relevance
        # TODO: Use AI-based ranking
        sorted_vendors = sorted(
            matching_vendors,
            key=lambda x: (x.get("performance_rating", 0), -x.get("risk_score", 100)),
            reverse=True,
        )

        return {
            "total_results": len(sorted_vendors),
            "vendors": sorted_vendors,
            "search_criteria": criteria,
        }

    async def _get_procurement_status(self, request_id: str) -> dict[str, Any]:
        """
        Get procurement request status.

        Returns detailed status information.
        """
        self.logger.info(f"Getting procurement status for request: {request_id}")

        request = self.procurement_requests.get(request_id)
        if not request:
            raise ValueError(f"Procurement request not found: {request_id}")

        # Find related RFP
        related_rfp = None
        for rfp_id, rfp in self.rfps.items():
            if rfp.get("request_id") == request_id:
                related_rfp = rfp
                break

        # Find related PO
        related_po = None
        if related_rfp and related_rfp.get("selected_vendor_id"):
            for po_number, po in self.purchase_orders.items():
                if po.get("vendor_id") == related_rfp.get("selected_vendor_id"):
                    related_po = po
                    break

        return {
            "request_id": request_id,
            "status": request.get("status"),
            "requester": request.get("requester"),
            "description": request.get("description"),
            "estimated_cost": request.get("estimated_cost"),
            "rfp_status": related_rfp.get("status") if related_rfp else None,
            "rfp_id": related_rfp.get("rfp_id") if related_rfp else None,
            "proposals_received": (
                len(related_rfp.get("proposals_received", [])) if related_rfp else 0
            ),
            "selected_vendor": related_rfp.get("selected_vendor_id") if related_rfp else None,
            "po_number": related_po.get("po_number") if related_po else None,
            "po_status": related_po.get("status") if related_po else None,
        }

    # Helper methods

    async def _generate_vendor_id(self) -> str:
        """Generate unique vendor ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"VND-{timestamp}"

    async def _generate_request_id(self) -> str:
        """Generate unique procurement request ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PR-{timestamp}"

    async def _generate_rfp_id(self) -> str:
        """Generate unique RFP ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"RFP-{timestamp}"

    async def _generate_proposal_id(self) -> str:
        """Generate unique proposal ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PROP-{timestamp}"

    async def _generate_contract_id(self) -> str:
        """Generate unique contract ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"CTR-{timestamp}"

    async def _generate_po_number(self) -> str:
        """Generate unique PO number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"PO-{timestamp}"

    async def _generate_invoice_id(self) -> str:
        """Generate unique invoice ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}"

    async def _run_compliance_checks(self, vendor_data: dict[str, Any]) -> dict[str, Any]:
        """Run compliance checks on vendor."""
        # TODO: Integrate with sanctions lists, anti-corruption databases
        return {"sanctions_check": "Pass", "anti_corruption_check": "Pass", "credit_check": "Pass"}

    async def _calculate_vendor_risk(
        self, vendor_data: dict[str, Any], compliance_checks: dict[str, Any]
    ) -> float:
        """Calculate vendor risk score (0-100, lower is better)."""
        # TODO: Use Azure ML for risk scoring
        base_risk = 50.0

        # Adjust for compliance
        if all(v == "Pass" for v in compliance_checks.values()):
            base_risk -= 10.0

        # Adjust for certifications
        if vendor_data.get("certifications"):
            base_risk -= 5.0

        return max(0, min(100, base_risk))

    async def _categorize_procurement_request(self, request_data: dict[str, Any]) -> str:
        """Categorize procurement request using AI."""
        # TODO: Use Azure ML for classification
        description = request_data.get("description", "").lower()

        if "software" in description or "license" in description:
            return "software"
        elif "cloud" in description or "aws" in description or "azure" in description:
            return "cloud"
        elif "consultant" in description or "consulting" in description:
            return "consulting"
        else:
            return "services"

    async def _check_budget_availability(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Check budget availability for procurement."""
        # TODO: Integrate with Financial Management Agent
        return {"available": True, "remaining_budget": 100000}

    async def _suggest_vendors(self, category: str, request_data: dict[str, Any]) -> list[str]:
        """Suggest vendors based on category and requirements."""
        # TODO: Use Azure ML for vendor recommendation
        suggested = []
        for vendor_id, vendor in self.vendors.items():
            if vendor.get("category") == category and vendor.get("status") == "Approved":
                suggested.append(vendor_id)

        return suggested[:5]  # Top 5

    async def _determine_approval_path(self, estimated_cost: float) -> str:
        """Determine approval path based on cost."""
        if estimated_cost > 100000:
            return "Executive Approval Required"
        elif estimated_cost > self.procurement_threshold:
            return "Manager Approval Required"
        else:
            return "Auto-Approved"

    async def _select_rfp_template(self, category: str) -> dict[str, Any]:
        """Select RFP template based on category."""
        # TODO: Load from template library
        return {"template_id": f"{category}_template", "sections": []}

    async def _generate_rfp_content(
        self, request: dict[str, Any], template: dict[str, Any], rfp_data: dict[str, Any]
    ) -> str:
        """Generate RFP content from template."""
        # TODO: Use Azure OpenAI for content generation
        return f"RFP for {request.get('description')}"

    async def _select_vendors_to_invite(
        self, category: str, suggested_vendors: list[str], specified_vendors: list[str]
    ) -> list[str]:
        """Select vendors to invite to RFP."""
        if specified_vendors:
            return specified_vendors
        return suggested_vendors[: self.min_vendor_proposals]

    async def _score_proposal(
        self, proposal: dict[str, Any], criteria: dict[str, float]
    ) -> dict[str, float]:
        """Score proposal against criteria."""
        # TODO: Use AI for automated scoring
        scores = {}

        # Cost score (inverse - lower cost = higher score)
        total_cost = proposal.get("pricing", {}).get("total", 100000)
        scores["cost"] = max(0, 100 - (total_cost / 1000))

        # Quality score (placeholder)
        scores["quality"] = 75.0

        # Delivery score (placeholder)
        scores["delivery"] = 80.0

        # Risk score (placeholder)
        scores["risk"] = 70.0

        # Diversity score (placeholder)
        scores["diversity"] = 50.0

        return scores

    async def _extract_contract_clauses(self, contract_data: dict[str, Any]) -> dict[str, Any]:
        """Extract key clauses from contract."""
        # TODO: Use Azure Form Recognizer
        return {
            "termination": "30 days notice",
            "liability": "Limited to contract value",
            "warranties": "Standard warranties apply",
        }

    async def _select_contract_template(self, contract_type: str) -> dict[str, Any]:
        """Select contract template."""
        # TODO: Load from template library
        return {"template_id": f"{contract_type}_contract"}

    async def _calculate_po_total(self, items: list[dict[str, Any]]) -> float:
        """Calculate total PO value."""
        total = 0.0
        for item in items:
            quantity = item.get("quantity", 1)
            unit_cost = item.get("unit_cost", 0)
            total += quantity * unit_cost
        return total

    async def _three_way_match(
        self, invoice: dict[str, Any], purchase_order: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform three-way matching between invoice, PO, and receipt."""
        discrepancies = []

        # Check amounts
        invoice_total = invoice.get("total_amount", 0)
        po_total = purchase_order.get("total_value", 0)

        if abs(invoice_total - po_total) > (po_total * self.invoice_tolerance_pct):
            discrepancies.append(
                {
                    "type": "amount_mismatch",
                    "invoice_amount": invoice_total,
                    "po_amount": po_total,
                    "variance": invoice_total - po_total,
                }
            )

        # TODO: Check line items
        # TODO: Check receipts

        return {"matched": len(discrepancies) == 0, "discrepancies": discrepancies}

    async def _initiate_payment(self, invoice: dict[str, Any]) -> dict[str, Any]:
        """Initiate payment in ERP."""
        # TODO: Integrate with ERP system
        return {
            "status": "Processing",
            "reference": f"PAY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        }

    async def _collect_vendor_performance_data(self, vendor_id: str) -> dict[str, Any]:
        """Collect vendor performance data."""
        # TODO: Query historical data
        return {"total_spend": 0, "contract_count": 0, "dispute_count": 0}

    async def _calculate_delivery_timeliness(self, vendor_id: str) -> float:
        """Calculate vendor delivery timeliness percentage."""
        # TODO: Calculate from historical deliveries
        return 95.0

    async def _calculate_quality_rating(self, vendor_id: str) -> float:
        """Calculate vendor quality rating."""
        # TODO: Calculate from quality metrics
        return 4.5  # Out of 5

    async def _calculate_compliance_score(self, vendor_id: str) -> float:
        """Calculate vendor compliance score."""
        # TODO: Calculate from compliance incidents
        return 98.0

    async def _calculate_sla_adherence(self, vendor_id: str) -> float:
        """Calculate SLA adherence percentage."""
        # TODO: Calculate from SLA tracking
        return 97.0

    async def _analyze_performance_trend(self, vendor_id: str) -> str:
        """Analyze vendor performance trend."""
        # TODO: Perform trend analysis
        return "Stable"

    async def _generate_vendor_recommendations(self, metrics: dict[str, Any]) -> list[str]:
        """Generate recommendations based on vendor metrics."""
        recommendations = []

        if metrics.get("delivery_timeliness", 100) < 90:
            recommendations.append("Improve delivery timeliness through SLA enforcement")

        if metrics.get("quality_rating", 5.0) < 4.0:
            recommendations.append("Address quality issues through corrective action plan")

        if not recommendations:
            recommendations.append("Continue current performance levels")

        return recommendations

    async def _get_vendor_contracts(self, vendor_id: str) -> list[dict[str, Any]]:
        """Get all contracts for a vendor."""
        vendor_contracts = []
        for contract_id, contract in self.contracts.items():
            if contract.get("vendor_id") == vendor_id:
                vendor_contracts.append(contract)
        return vendor_contracts

    async def _get_vendor_issues(self, vendor_id: str) -> list[dict[str, Any]]:
        """Get recent issues with vendor."""
        # TODO: Query issue tracking system
        return []

    async def _calculate_overall_vendor_score(self, vendor: dict[str, Any]) -> float:
        """Calculate overall vendor score."""
        metrics = vendor.get("performance_metrics", {})
        risk_score = vendor.get("risk_score", 50)

        # Weighted average
        score = (
            metrics.get("quality_rating", 0) * 20
            + metrics.get("on_time_delivery_rate", 0) * 20
            + metrics.get("compliance_rating", 0) * 20
            + (100 - risk_score) * 20
            + metrics.get("sla_adherence", 0) * 20
        ) / 100

        return min(100, max(0, score))  # type: ignore

    async def _is_expiring_soon(self, contract: dict[str, Any]) -> bool:
        """Check if contract is expiring within 90 days."""
        end_date_str = contract.get("end_date")
        if not end_date_str:
            return False

        end_date = datetime.fromisoformat(end_date_str)
        days_until_expiry = (end_date - datetime.utcnow()).days
        return 0 < days_until_expiry <= 90

    async def _matches_criteria(self, vendor: dict[str, Any], criteria: dict[str, Any]) -> bool:
        """Check if vendor matches search criteria."""
        if "category" in criteria and vendor.get("category") != criteria["category"]:
            return False

        if "min_rating" in criteria:
            if (
                vendor.get("performance_metrics", {}).get("quality_rating", 0)
                < criteria["min_rating"]
            ):
                return False

        if "max_risk_score" in criteria:
            if vendor.get("risk_score", 100) > criteria["max_risk_score"]:
                return False

        if "status" in criteria and vendor.get("status") != criteria["status"]:
            return False

        return True

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self.logger.info("Cleaning up Vendor & Procurement Management Agent...")
        # TODO: Close database connections
        # TODO: Close ERP connections
        # TODO: Close external API connections
        # TODO: Flush any pending events

    def get_capabilities(self) -> list[str]:
        """Return list of agent capabilities."""
        return [
            "vendor_registry",
            "vendor_onboarding",
            "vendor_risk_scoring",
            "procurement_request_intake",
            "rfp_generation",
            "rfp_quote_management",
            "vendor_selection",
            "vendor_scoring",
            "contract_management",
            "purchase_order_creation",
            "purchase_order_approval",
            "invoice_receipt",
            "invoice_reconciliation",
            "three_way_matching",
            "vendor_performance_monitoring",
            "vendor_scorecard_generation",
            "compliance_enforcement",
            "audit_trail_management",
            "spend_analysis",
        ]
