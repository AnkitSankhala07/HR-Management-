from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.employees.models import Department, Designation, Employee
from apps.recruitment.models import Job, Candidate, Application


class Command(BaseCommand):
    help = "Seeds comprehensive sample jobs and candidate data for the careers portal."

    def handle(self, *args, **options):
        self.stdout.write("Seeding career portal sample jobs...")

        depts = {d.name: d for d in Department.objects.all()}
        eng = depts.get("Engineering")
        hr = depts.get("HR")
        fin = depts.get("Finance")
        mkt = depts.get("Marketing")
        sales = depts.get("Sales")

        hiring_mgr = Employee.objects.filter(user__role__in=["MANAGER", "HR_ADMIN", "ADMIN"]).first()
        now = timezone.now()

        sample_jobs = [
            {
                "title": "Senior Python / Django Backend Engineer",
                "department": eng,
                "location": "Ahmedabad (HQ) / Hybrid",
                "employment_type": "FULL_TIME",
                "experience_min": 4,
                "skills_required": "Python, Django, DRF, PostgreSQL, Redis, Celery, Docker",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=1),
                "description": (
                    "About the Role:\n"
                    "We are looking for an experienced Senior Backend Engineer to architect, build, and scale our core Dayflow HRMS APIs and asynchronous service layer. You will collaborate closely with product and frontend engineering to design high-throughput, mission-critical systems that thousands of employees depend on every day.\n\n"
                    "Key Responsibilities:\n"
                    "• Design resilient REST APIs, background job queues, and transactional workflows.\n"
                    "• Optimize database query performance, indexing, and connection pools for PostgreSQL / MySQL.\n"
                    "• Implement role-based security, multi-tenant data isolation, and comprehensive audit logs.\n"
                    "• Write automated test suites (unit, integration, and load tests) and conduct rigorous code reviews.\n"
                    "• Mentor junior engineers and champion clean code standards.\n\n"
                    "What We're Looking For:\n"
                    "• 4+ years of professional backend development using Python and Django/FastAPI.\n"
                    "• Deep understanding of relational databases (PostgreSQL/MySQL), relational schema design, and query optimization.\n"
                    "• Hands-on experience with caching strategies (Redis), task queues (Celery), and containerization (Docker).\n"
                    "• Solid understanding of authentication protocols, RBAC, OAuth2, and web security best practices.\n\n"
                    "Benefits & Perks:\n"
                    "• Competitive compensation package with equity options.\n"
                    "• Flexible hybrid work schedule and premium health coverage.\n"
                    "• Annual learning stipend (₹60,000/yr) for courses, books, and tech conferences."
                ),
            },
            {
                "title": "Senior Frontend Engineer (React & TypeScript)",
                "department": eng,
                "location": "Remote - India / Ahmedabad",
                "employment_type": "FULL_TIME",
                "experience_min": 3,
                "skills_required": "React, TypeScript, Next.js, TailwindCSS, State Management, WebSockets",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=2),
                "description": (
                    "About the Role:\n"
                    "Dayflow is searching for a passionate Frontend Engineer who cares deeply about UI craftsmanship, micro-interactions, and lightning-fast web performance. You will build intuitive, responsive dashboards, interactive kanban boards, and real-time attendance timelines for our workforce platform.\n\n"
                    "Key Responsibilities:\n"
                    "• Build modular, accessible UI components and maintain our unified design token system.\n"
                    "• Collaborate with designers to translate complex HR workflows into elegant, friction-free interactions.\n"
                    "• Optimize frontend bundle sizes, Core Web Vitals, and client-side rendering speed.\n"
                    "• Implement real-time notifications, chat features, and dynamic charting.\n\n"
                    "What We're Looking For:\n"
                    "• 3+ years of building modern SPAs with React, TypeScript, and modern CSS/Tailwind.\n"
                    "• Strong grasp of modern JavaScript (ES6+), DOM rendering lifecycles, and state management.\n"
                    "• An eye for detail: typography, spacing, transitions, and accessibility (WCAG AA).\n"
                    "• Experience with testing libraries (Jest, Playwright or Cypress) is a plus.\n\n"
                    "Benefits & Perks:\n"
                    "• 100% remote flexibility with home office setup reimbursement.\n"
                    "• Top-tier hardware (MacBook Pro + 4K display).\n"
                    "• Generous paid time off and quarterly team offsites."
                ),
            },
            {
                "title": "AI & Machine Learning Engineer (HR Copilot)",
                "department": eng,
                "location": "Ahmedabad (HQ) / Hybrid",
                "employment_type": "FULL_TIME",
                "experience_min": 3,
                "skills_required": "Python, LLMs, LangChain, RAG, Vector DBs, PyTorch, FastAPI",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=3),
                "description": (
                    "About the Role:\n"
                    "Be part of the team shaping Dayflow's AI HR Copilot. You will build intelligent question-answering systems, policy retrieval agents (RAG), and proactive workflow assistants that respect enterprise data governance and permission boundaries.\n\n"
                    "Key Responsibilities:\n"
                    "• Develop and evaluate Retrieval-Augmented Generation (RAG) pipelines for HR company policies and handbook Q&A.\n"
                    "• Build agentic workflows for automated employee scheduling, leave recommendations, and smart payroll anomaly detection.\n"
                    "• Implement safety guardrails, prompt evaluation harnesses, and hallucination reduction mechanisms.\n"
                    "• Serve models via low-latency microservices with streaming token responses.\n\n"
                    "What We're Looking For:\n"
                    "• 3+ years working in Machine Learning, NLP, or LLM application engineering.\n"
                    "• Practical expertise with OpenAI/Anthropic/Gemini APIs, Hugging Face, vector databases (e.g. pgvector, Qdrant), and embeddings.\n"
                    "• Production Python experience and familiarity with FastAPI or Django.\n\n"
                    "Benefits & Perks:\n"
                    "• Dedicated GPU compute cloud budget for model research and prototyping.\n"
                    "• Competitive compensation, equity, and comprehensive family health insurance."
                ),
            },
            {
                "title": "Cloud DevOps & Infrastructure Engineer",
                "department": eng,
                "location": "Remote - India",
                "employment_type": "FULL_TIME",
                "experience_min": 3,
                "skills_required": "AWS, Docker, Kubernetes, Terraform, CI/CD, GitHub Actions, Prometheus",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=4),
                "description": (
                    "About the Role:\n"
                    "We need a Cloud DevOps Engineer to spearhead our infrastructure reliability, continuous delivery pipelines, and zero-downtime deployment strategies across multi-region cloud clusters.\n\n"
                    "Key Responsibilities:\n"
                    "• Automate infrastructure provisioning using Terraform / OpenTofu and Infrastructure-as-Code.\n"
                    "• Maintain and monitor high-availability Kubernetes clusters, load balancers, and CDN caching layers.\n"
                    "• Enhance CI/CD pipelines in GitHub Actions for automated unit testing, container scanning, and staging deployments.\n"
                    "• Establish comprehensive observability with Prometheus, Grafana, OpenTelemetry, and structured log alerting.\n\n"
                    "What We're Looking For:\n"
                    "• 3+ years managing production cloud workloads on AWS or GCP.\n"
                    "• Strong proficiency with Linux system administration, networking, TLS, and Docker container security.\n"
                    "• Experience with automated database backup, point-in-time recovery, and disaster recovery drills.\n\n"
                    "Benefits & Perks:\n"
                    "• Fully remote role with flexible working hours.\n"
                    "• Annual wellness and fitness stipend."
                ),
            },
            {
                "title": "Principal Product Manager (People Tech & Workflows)",
                "department": eng,
                "location": "Ahmedabad / Hybrid",
                "employment_type": "FULL_TIME",
                "experience_min": 5,
                "skills_required": "Product Strategy, User Research, Roadmapping, Agile/Scrum, B2B SaaS",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=5),
                "description": (
                    "About the Role:\n"
                    "As Principal Product Manager, you will define the product vision, strategy, and execution roadmap for Dayflow's core workforce management modules including Payroll, Performance, and Employee Lifecycle.\n\n"
                    "Key Responsibilities:\n"
                    "• Deeply understand HR leaders, managers, and employees through continuous customer discovery interviews.\n"
                    "• Author detailed PRDs, user stories, and measurable success criteria (KPIs / OKRs).\n"
                    "• Partner closely with design and engineering teams through rapid sprint cycles and iterative releases.\n"
                    "• Track adoption metrics, funnels, and customer feedback to guide continuous product iteration.\n\n"
                    "What We're Looking For:\n"
                    "• 5+ years of software product management experience, preferably in B2B SaaS, HR tech, or fintech.\n"
                    "• Proven track record of shipping complex enterprise features with outstanding adoption rates.\n"
                    "• Exceptional written, oral, and analytical communication skills.\n\n"
                    "Benefits & Perks:\n"
                    "• Leadership role with substantial company equity.\n"
                    "• Executive mentoring and international conference sponsorship."
                ),
            },
            {
                "title": "Lead Product UI/UX Designer",
                "department": eng,
                "location": "Ahmedabad (HQ) / Hybrid",
                "employment_type": "FULL_TIME",
                "experience_min": 4,
                "skills_required": "Figma, Design Systems, UX Research, Prototyping, Wireframing, Micro-interactions",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=3),
                "description": (
                    "About the Role:\n"
                    "Enterprise software doesn't have to be clunky or boring. We are looking for a Lead UI/UX Designer to craft consumer-grade, joyful digital experiences for Dayflow HRMS across desktop and mobile browsers.\n\n"
                    "Key Responsibilities:\n"
                    "• Own and evolve the Dayflow design system in Figma (components, typography, color tokens, and animation curves).\n"
                    "• Produce low-fidelity wireframes, interactive prototypes, and production-ready high-fidelity UI specifications.\n"
                    "• Conduct usability testing sessions with actual HR admins and employees to uncover friction points.\n"
                    "• Collaborate with frontend developers to ensure design fidelity in production builds.\n\n"
                    "What We're Looking For:\n"
                    "• 4+ years of UI/UX design experience for complex web applications or mobile apps.\n"
                    "• A strong portfolio demonstrating systematic design thinking, craft, and clean typographic hierarchy.\n"
                    "• Mastery of Figma (auto-layout, components, variants, design tokens).\n\n"
                    "Benefits & Perks:\n"
                    "• Creative freedom to define our visual design language.\n"
                    "• Annual design conference and workshop pass."
                ),
            },
            {
                "title": "Senior Talent Acquisition & People Operations Partner",
                "department": hr,
                "location": "Ahmedabad (HQ)",
                "employment_type": "FULL_TIME",
                "experience_min": 3,
                "skills_required": "Technical Recruiting, HR Operations, Employee Engagement, Onboarding, Culture",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=2),
                "description": (
                    "About the Role:\n"
                    "Help us attract, hire, and nurture the brightest engineering, product, and business talent. You will run end-to-end recruitment pipelines and spearhead employee engagement initiatives at Dayflow.\n\n"
                    "Key Responsibilities:\n"
                    "• Source, screen, and interview candidates for high-priority technical and go-to-market roles.\n"
                    "• Partner with hiring managers to define job specifications, interview scorecards, and offer packages.\n"
                    "• Deliver a world-class candidate experience from first outreach to onboarding day.\n"
                    "• Drive internal employee culture programs, quarterly reviews, and pulse surveys.\n\n"
                    "What We're Looking For:\n"
                    "• 3+ years in tech recruiting and people operations in a fast-paced technology company.\n"
                    "• Excellent communication and negotiation skills with a human-centric approach.\n"
                    "• Familiarity with modern ATS platforms and employment regulations.\n\n"
                    "Benefits & Perks:\n"
                    "• Competitive salary plus performance hiring bonuses.\n"
                    "• Comprehensive medical insurance and healthy cafeteria meals."
                ),
            },
            {
                "title": "B2B SaaS Growth & Product Marketing Specialist",
                "department": mkt,
                "location": "Remote - India / Hybrid",
                "employment_type": "FULL_TIME",
                "experience_min": 2,
                "skills_required": "Product Marketing, Content Strategy, SEO, B2B Lead Gen, Copywriting, Analytics",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=4),
                "description": (
                    "About the Role:\n"
                    "Drive inbound demand, product storytelling, and customer case studies for Dayflow HRMS. You will craft compelling messaging that positions Dayflow as the leading modern HR platform for growing businesses.\n\n"
                    "Key Responsibilities:\n"
                    "• Write high-converting landing page copy, technical product walkthroughs, and SEO articles.\n"
                    "• Lead email marketing campaigns and automated onboarding sequences for prospect signups.\n"
                    "• Manage social channels and community presence across LinkedIn, Twitter, and tech forums.\n"
                    "• Analyze conversion funnels and run A/B testing on call-to-action touchpoints.\n\n"
                    "What We're Looking For:\n"
                    "• 2+ years of experience in product marketing, content creation, or growth for B2B SaaS.\n"
                    "• Impeccable written and verbal English communication skills.\n"
                    "• Experience with Google Analytics, Search Console, and marketing automation tools.\n\n"
                    "Benefits & Perks:\n"
                    "• Remote work environment with high autonomy.\n"
                    "• Generous performance incentives."
                ),
            },
            {
                "title": "Enterprise Account Executive (HR Tech Sales)",
                "department": sales,
                "location": "Bengaluru / Mumbai / Remote",
                "employment_type": "FULL_TIME",
                "experience_min": 3,
                "skills_required": "Enterprise Sales, Solution Selling, Demo Presentation, B2B SaaS, CRM",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=5),
                "description": (
                    "About the Role:\n"
                    "We are seeking an ambitious Enterprise Account Executive to engage with CHROs, HR Directors, and CEOs to demonstrate how Dayflow transforms workforce management, attendance, and payroll operations.\n\n"
                    "Key Responsibilities:\n"
                    "• Manage the full sales cycle from discovery calls and product demos to contract negotiation and closing.\n"
                    "• Identify customer pain points and articulate tailored value propositions.\n"
                    "• Partner with customer success for seamless account handoff and post-onboarding satisfaction.\n"
                    "• Maintain pipeline hygiene and forecasting in CRM.\n\n"
                    "What We're Looking For:\n"
                    "• 3+ years in quota-carrying B2B software sales, preferably in HRMS, ERP, or SaaS.\n"
                    "• Proven track record of consistently exceeding quarterly revenue targets.\n"
                    "• Strong presentation and consultative closing skills.\n\n"
                    "Benefits & Perks:\n"
                    "• Uncapped sales commissions with competitive base salary.\n"
                    "• Travel allowance and tech package."
                ),
            },
            {
                "title": "Financial Analyst & Compensation Planning Specialist",
                "department": fin,
                "location": "Ahmedabad (HQ)",
                "employment_type": "FULL_TIME",
                "experience_min": 2,
                "skills_required": "Financial Modeling, Payroll Analytics, Excel/Google Sheets, Budgeting, Taxation",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=6),
                "description": (
                    "About the Role:\n"
                    "Join our Finance team to assist with compensation benchmarking, payroll ledger auditing, budget forecasts, and financial compliance for Dayflow.\n\n"
                    "Key Responsibilities:\n"
                    "• Perform compensation and benefits benchmarking against market data.\n"
                    "• Reconcile monthly payroll registers, statutory deductions (PF, ESI, TDS), and expense reports.\n"
                    "• Build financial models for headcount planning, salary revision projections, and operational cash flow.\n"
                    "• Support quarterly financial audit preparations and management dashboards.\n\n"
                    "What We're Looking For:\n"
                    "• Bachelor's or Master's degree in Finance, Accounting, or Commerce (CA / MBA Finance preferred).\n"
                    "• 2+ years of relevant experience in corporate finance or payroll analytics.\n"
                    "• Advanced Excel/Sheets proficiency (lookups, pivot tables, financial formulas).\n\n"
                    "Benefits & Perks:\n"
                    "• Clear path for career growth and professional certification support.\n"
                    "• Full medical benefits and generous paid leave."
                ),
            },
            {
                "title": "Software Engineering Intern (Summer / Fall 2026)",
                "department": eng,
                "location": "Ahmedabad (HQ) / Hybrid",
                "employment_type": "INTERNSHIP",
                "experience_min": 0,
                "skills_required": "Python, JavaScript, HTML/CSS, Git, Computer Science Fundamentals",
                "status": Job.Status.OPEN,
                "published_at": now - timedelta(days=1),
                "description": (
                    "About the Role:\n"
                    "Kickstart your career with Dayflow! As a Software Engineering Intern, you will work on real production features alongside experienced mentors. You'll write code, participate in sprint planning, and see your work used by thousands of employees.\n\n"
                    "Key Responsibilities:\n"
                    "• Build new features and bug fixes across backend APIs (Python/Django) and frontend interfaces.\n"
                    "• Participate in team code reviews, daily standups, and architecture discussions.\n"
                    "• Write clean unit and integration tests for your contributions.\n"
                    "• Learn modern software engineering practices, CI/CD, and scalable web design.\n\n"
                    "What We're Looking For:\n"
                    "• Current student or recent graduate in Computer Science, IT, or related technical field.\n"
                    "• Familiarity with Python, JavaScript, and web fundamentals.\n"
                    "• Curiosity, eagerness to learn, and strong problem-solving skills.\n\n"
                    "Benefits & Perks:\n"
                    "• Competitive paid monthly stipend.\n"
                    "• Pre-placement offer (PPO) opportunities for high-performing interns.\n"
                    "• Free lunches, snacks, and mentorship."
                ),
            },
        ]

        created_count = 0
        updated_count = 0

        for item in sample_jobs:
            job, created = Job.objects.update_or_create(
                title=item["title"],
                defaults={
                    "department": item["department"],
                    "hiring_manager": hiring_mgr,
                    "location": item["location"],
                    "employment_type": item["employment_type"],
                    "experience_min": item["experience_min"],
                    "skills_required": item["skills_required"],
                    "status": item["status"],
                    "published_at": item["published_at"],
                    "description": item["description"],
                }
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully processed {len(sample_jobs)} jobs ({created_count} created, {updated_count} updated)."))
