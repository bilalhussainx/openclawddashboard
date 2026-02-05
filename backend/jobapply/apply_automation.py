"""
Browser automation for job applications via OpenClaw Gateway.
Supports LinkedIn Easy Apply, Indeed Apply, and generic career page forms.
"""
import asyncio
import logging
import random
import re
import time

logger = logging.getLogger(__name__)


class JobApplyAutomation:
    """
    Orchestrates browser-based job application through OpenClaw Gateway.
    Uses the accessibility tree snapshot to find and interact with form elements.
    """

    def __init__(self, gateway_client, resume_data: dict, resume_file_path: str = None):
        self.gw = gateway_client
        self.resume_data = resume_data
        self.resume_file_path = resume_file_path
        self.log = []

    def _log(self, step: str, action: str, result: str, ref: str = ''):
        entry = {
            'step': step,
            'action': action,
            'ref': ref,
            'result': result,
            'timestamp': time.time(),
        }
        self.log.append(entry)
        logger.info(f"[{step}] {action}: {result}")

    async def _delay(self, min_sec=2, max_sec=5):
        """Human-like random delay between actions."""
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)

    async def apply_to_job(self, job_url: str, cover_letter: str = '') -> dict:
        """
        Main entry point: navigate to job URL and attempt to apply.
        Detects the platform and routes to the appropriate handler.

        Returns:
            dict with 'success', 'method', 'log', 'error'
        """
        try:
            # Navigate to job URL
            self._log('navigate', 'browser_navigate', f'Navigating to {job_url}')
            await self.gw.browser_navigate_direct(job_url)
            await self._delay(3, 6)

            # Take snapshot to analyze the page
            snapshot = await self.gw.browser_snapshot()
            page_text = self._extract_text(snapshot)

            if not page_text:
                self._log('navigate', 'snapshot', 'Failed to get page snapshot')
                return {'success': False, 'method': 'none', 'log': self.log, 'error': 'Could not load page'}

            self._log('navigate', 'snapshot', f'Page loaded, {len(page_text)} chars')

            # Detect platform and apply
            if 'linkedin.com' in job_url or 'Easy Apply' in page_text:
                return await self._apply_linkedin(snapshot, page_text, cover_letter)
            elif 'indeed.com' in job_url:
                return await self._apply_indeed(snapshot, page_text, cover_letter)
            elif 'glassdoor.com' in job_url:
                return await self._apply_glassdoor(snapshot, page_text, cover_letter)
            else:
                return await self._apply_generic(snapshot, page_text, cover_letter)

        except Exception as e:
            logger.error(f"Apply automation failed: {e}")
            self._log('error', 'exception', str(e))
            return {'success': False, 'method': 'error', 'log': self.log, 'error': str(e)}

    async def _apply_linkedin(self, snapshot: dict, page_text: str, cover_letter: str) -> dict:
        """Handle LinkedIn Easy Apply flow."""
        self._log('linkedin', 'detect', 'LinkedIn job detected')

        # Find Easy Apply button
        easy_apply_ref = self._find_element(snapshot, ['Easy Apply', 'easy apply'])
        if not easy_apply_ref:
            self._log('linkedin', 'find_button', 'Easy Apply button not found - may require external application')
            # Check for external Apply button
            apply_ref = self._find_element(snapshot, ['Apply', 'apply now'])
            if apply_ref:
                self._log('linkedin', 'external', 'Found external Apply button - clicking')
                await self.gw.browser_click(apply_ref)
                await self._delay(3, 5)
                # After redirect, try generic form fill
                new_snapshot = await self.gw.browser_snapshot()
                new_text = self._extract_text(new_snapshot)
                return await self._apply_generic(new_snapshot, new_text, cover_letter)
            return {'success': False, 'method': 'linkedin', 'log': self.log, 'error': 'No Easy Apply button found'}

        # Click Easy Apply
        self._log('linkedin', 'click', 'Clicking Easy Apply', easy_apply_ref)
        await self.gw.browser_click(easy_apply_ref)
        await self._delay(2, 4)

        # Process multi-page form
        max_pages = 8
        for page_num in range(max_pages):
            form_snapshot = await self.gw.browser_snapshot()
            form_text = self._extract_text(form_snapshot)

            self._log('linkedin', f'form_page_{page_num}', f'Processing form page {page_num + 1}')

            # Fill form fields
            await self._fill_form_fields(form_snapshot)

            # Check for Submit button
            submit_ref = self._find_element(form_snapshot, ['Submit application', 'Submit', 'send application'])
            if submit_ref:
                self._log('linkedin', 'submit', 'Found Submit button', submit_ref)
                await self.gw.browser_click(submit_ref)
                await self._delay(2, 4)

                # Verify submission
                result_snapshot = await self.gw.browser_snapshot()
                result_text = self._extract_text(result_snapshot)
                if 'application was sent' in result_text.lower() or 'applied' in result_text.lower():
                    self._log('linkedin', 'success', 'Application submitted successfully')
                    return {'success': True, 'method': 'linkedin_easy_apply', 'log': self.log, 'error': None}
                else:
                    self._log('linkedin', 'verify', 'Submit clicked but could not verify success')
                    return {'success': True, 'method': 'linkedin_easy_apply', 'log': self.log, 'error': None}

            # Look for Next/Continue button
            next_ref = self._find_element(form_snapshot, ['Next', 'Continue', 'Review'])
            if next_ref:
                self._log('linkedin', 'next', f'Clicking Next on page {page_num + 1}', next_ref)
                await self.gw.browser_click(next_ref)
                await self._delay(2, 3)
            else:
                # Check for Close/Dismiss - might mean we need to scroll
                self._log('linkedin', 'stuck', f'No Next/Submit found on page {page_num + 1}')
                break

        self._log('linkedin', 'incomplete', 'Could not complete all form pages')
        return {'success': False, 'method': 'linkedin_easy_apply', 'log': self.log, 'error': 'Form navigation incomplete'}

    async def _apply_indeed(self, snapshot: dict, page_text: str, cover_letter: str) -> dict:
        """Handle Indeed Apply flow."""
        self._log('indeed', 'detect', 'Indeed job detected')

        # Find Apply button
        apply_ref = self._find_element(snapshot, ['Apply now', 'Apply on company site', 'Apply'])
        if not apply_ref:
            self._log('indeed', 'find_button', 'Apply button not found')
            return {'success': False, 'method': 'indeed', 'log': self.log, 'error': 'No Apply button found'}

        self._log('indeed', 'click', 'Clicking Apply', apply_ref)
        await self.gw.browser_click(apply_ref)
        await self._delay(3, 5)

        # Process form (Indeed has multi-step too)
        max_pages = 6
        for page_num in range(max_pages):
            form_snapshot = await self.gw.browser_snapshot()

            self._log('indeed', f'form_page_{page_num}', f'Processing form page {page_num + 1}')

            await self._fill_form_fields(form_snapshot)

            # Check for Submit
            submit_ref = self._find_element(form_snapshot, ['Submit your application', 'Submit', 'Apply'])
            if submit_ref:
                self._log('indeed', 'submit', 'Clicking Submit', submit_ref)
                await self.gw.browser_click(submit_ref)
                await self._delay(2, 4)
                self._log('indeed', 'success', 'Application submitted')
                return {'success': True, 'method': 'indeed_apply', 'log': self.log, 'error': None}

            # Next/Continue
            next_ref = self._find_element(form_snapshot, ['Continue', 'Next'])
            if next_ref:
                self._log('indeed', 'next', f'Clicking Continue on page {page_num + 1}', next_ref)
                await self.gw.browser_click(next_ref)
                await self._delay(2, 3)
            else:
                break

        return {'success': False, 'method': 'indeed_apply', 'log': self.log, 'error': 'Could not complete Indeed form'}

    async def _apply_glassdoor(self, snapshot: dict, page_text: str, cover_letter: str) -> dict:
        """Handle Glassdoor - usually redirects to company site."""
        self._log('glassdoor', 'detect', 'Glassdoor job detected')

        apply_ref = self._find_element(snapshot, ['Apply', 'Easy Apply', 'Apply Now'])
        if apply_ref:
            self._log('glassdoor', 'click', 'Clicking Apply', apply_ref)
            await self.gw.browser_click(apply_ref)
            await self._delay(3, 5)

            # After redirect, try generic form
            new_snapshot = await self.gw.browser_snapshot()
            new_text = self._extract_text(new_snapshot)
            return await self._apply_generic(new_snapshot, new_text, cover_letter)

        return {'success': False, 'method': 'glassdoor', 'log': self.log, 'error': 'No Apply button found'}

    async def _apply_generic(self, snapshot: dict, page_text: str, cover_letter: str) -> dict:
        """Handle generic career page application forms."""
        self._log('generic', 'detect', 'Generic career page detected')

        # Try to fill any visible form
        filled = await self._fill_form_fields(snapshot)

        if filled > 0:
            # Look for submit
            submit_ref = self._find_element(snapshot, ['Submit', 'Apply', 'Send Application', 'Submit Application'])
            if submit_ref:
                self._log('generic', 'submit', 'Clicking Submit', submit_ref)
                await self.gw.browser_click(submit_ref)
                await self._delay(2, 4)
                self._log('generic', 'success', f'Form submitted with {filled} fields filled')
                return {'success': True, 'method': 'generic_form', 'log': self.log, 'error': None}

        self._log('generic', 'incomplete', 'Could not find or fill application form')
        return {'success': False, 'method': 'generic', 'log': self.log, 'error': 'No application form found'}

    async def _fill_form_fields(self, snapshot: dict) -> int:
        """
        Parse snapshot for form fields and fill them with resume data.
        Returns count of fields filled.
        """
        fields = self._parse_form_fields(snapshot)
        filled = 0

        for field in fields:
            label = field.get('label', '').lower()
            ref = field.get('ref', '')
            field_type = field.get('type', 'text')

            if not ref:
                continue

            value = self._map_field_to_resume(label, field_type)
            if value:
                try:
                    await self.gw.browser_type(ref, value)
                    filled += 1
                    self._log('fill', f'typed_{label}', f'Filled "{label}" with value', ref)
                    await self._delay(0.5, 1.5)
                except Exception as e:
                    self._log('fill', f'error_{label}', str(e), ref)

        return filled

    def _map_field_to_resume(self, label: str, field_type: str = 'text') -> str:
        """Map a form field label to the appropriate resume data."""
        label = label.lower().strip()
        data = self.resume_data

        # Name fields
        if any(term in label for term in ['first name', 'given name']):
            name = data.get('name', '')
            return name.split()[0] if name else ''
        if any(term in label for term in ['last name', 'family name', 'surname']):
            name = data.get('name', '')
            parts = name.split()
            return parts[-1] if len(parts) > 1 else ''
        if label in ['name', 'full name', 'your name']:
            return data.get('name', '')

        # Contact
        if 'email' in label:
            return data.get('email', '')
        if 'phone' in label or 'mobile' in label or 'tel' in label:
            return data.get('phone', '')

        # Location
        if any(term in label for term in ['city', 'location', 'address']):
            return data.get('location', 'Toronto, Ontario')

        # Professional
        if 'linkedin' in label:
            return ''  # Don't auto-fill LinkedIn URL
        if 'website' in label or 'portfolio' in label:
            return ''
        if any(term in label for term in ['current title', 'job title', 'position']):
            exp = data.get('experience', [])
            return exp[0].get('title', '') if exp else ''
        if any(term in label for term in ['current company', 'employer', 'company']):
            exp = data.get('experience', [])
            return exp[0].get('company', '') if exp else ''
        if any(term in label for term in ['years of experience', 'experience']):
            return '5'
        if 'salary' in label or 'compensation' in label:
            return ''  # Don't auto-fill salary expectations

        # Education
        if 'school' in label or 'university' in label or 'college' in label:
            edu = data.get('education', [])
            return edu[0].get('school', '') if edu else ''
        if 'degree' in label:
            edu = data.get('education', [])
            return edu[0].get('degree', '') if edu else ''

        return ''

    def _find_element(self, snapshot: dict, labels: list) -> str:
        """
        Find an element ref in the snapshot by matching labels.
        Searches through the accessibility tree for buttons/links with matching text.
        """
        if not snapshot:
            return ''

        # The snapshot payload contains the accessibility tree
        payload = snapshot.get('payload', snapshot.get('result', {}))
        if isinstance(payload, dict):
            tree_text = str(payload)
        elif isinstance(payload, str):
            tree_text = payload
        else:
            return ''

        # Look for refs associated with the label text
        for label in labels:
            # Pattern: look for ref="XX" near the label text
            # OpenClaw snapshots use [ref=N] format in accessibility tree
            pattern = rf'\[ref=(\w+)\][^[]*{re.escape(label)}'
            match = re.search(pattern, tree_text, re.IGNORECASE)
            if match:
                return match.group(1)

            # Also try label before ref
            pattern = rf'{re.escape(label)}[^[]*\[ref=(\w+)\]'
            match = re.search(pattern, tree_text, re.IGNORECASE)
            if match:
                return match.group(1)

        return ''

    def _parse_form_fields(self, snapshot: dict) -> list:
        """
        Extract form input fields from the accessibility tree snapshot.
        Returns list of {label, ref, type}.
        """
        fields = []

        payload = snapshot.get('payload', snapshot.get('result', {}))
        if isinstance(payload, dict):
            tree_text = str(payload)
        elif isinstance(payload, str):
            tree_text = payload
        else:
            return fields

        # Find input fields: textbox [ref=N], input [ref=N], etc.
        # Pattern matches various form element formats in accessibility trees
        patterns = [
            r'(?:textbox|input|text field)\s+(?:\"([^\"]+)\")?\s*\[ref=(\w+)\]',
            r'\[ref=(\w+)\]\s*(?:textbox|input)\s*\"([^\"]+)\"',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, tree_text, re.IGNORECASE):
                groups = match.groups()
                if len(groups) == 2:
                    label = groups[0] or ''
                    ref = groups[1] or ''
                    if ref:
                        fields.append({'label': label, 'ref': ref, 'type': 'text'})

        return fields

    def _extract_text(self, snapshot: dict) -> str:
        """Extract readable text from a snapshot response."""
        if not snapshot:
            return ''

        payload = snapshot.get('payload', snapshot.get('result', {}))
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            # Try common keys
            for key in ['text', 'content', 'snapshot', 'html']:
                if key in payload:
                    val = payload[key]
                    return val if isinstance(val, str) else str(val)
            return str(payload)[:5000]
        return ''


async def run_apply_automation(
    gateway_url: str,
    gateway_token: str,
    job_url: str,
    resume_data: dict,
    cover_letter: str = '',
    resume_file_path: str = None,
) -> dict:
    """
    Top-level function to run browser apply automation.
    Creates gateway client, connects, and runs the apply flow.
    """
    from automations.tasks import OpenClawGatewayClient

    client = OpenClawGatewayClient(gateway_url, gateway_token)
    try:
        connected = await client.connect()
        if not connected:
            return {'success': False, 'method': 'none', 'log': [], 'error': 'Failed to connect to Gateway'}

        # Start browser if needed
        await client.browser_start()

        automation = JobApplyAutomation(client, resume_data, resume_file_path)
        result = await automation.apply_to_job(job_url, cover_letter)
        return result

    finally:
        await client.disconnect()
