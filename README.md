# QCBM-LSTM: Quantum Circuit Born Machine with LSTM Architecture

A quantum machine learning project implementing Quantum Circuit Born Machine (QCBM) enhanced with Long Short-Term Memory (LSTM) networks for advanced pattern recognition and generation tasks.

## 🚀 Quick Start - Cloud Development Environment

Deploy a complete AWS development environment in 3 simple steps:

### 1. Deploy Infrastructure (5 minutes)

```bash
# Deploy with project name
./deploy-cpu.sh qcbm

# Or with custom name
./deploy-cpu.sh myproject
```

### 2. Setup SSH Access

```bash
# Setup SSH configuration
./setup-ssh.sh qcbm
```

### 3. Connect & Develop

```bash
# SSH to EC2 instance
ssh qcbm

# SSH to Docker container (recommended for development)
ssh qcbm-container
```

### 4. Access Web Interfaces

- **Jupyter Notebook**: `http://YOUR_ELASTIC_IP:8888` (token: `qcbmtoken`)
- **VSCode Web**: `http://YOUR_ELASTIC_IP:8080`

## 💰 Cost Information

- **t3.large CPU instance**: ~$0.09/hour (~$65/month)
- **50GB EBS storage**: ~$5/month
- **Elastic IP**: Free when attached to running instance

## 🔧 Local Development

For local development without cloud infrastructure:

```bash
# Install dependencies
pip install -r requirements.txt

# Run Jupyter locally
jupyter notebook
```

## 📊 Project Structure

```
QCBM-LSTM/
├── deploy-cpu.sh           # Quick cloud deployment
├── setup-ssh.sh           # SSH configuration setup
├── .infra/                 # Infrastructure automation (hidden - ignore this!)
│   ├── cloudformation-cpu.yml
│   ├── deploy-cpu.sh
│   ├── setup_ssh_config.sh
│   └── Dockerfile
├── src/                    # Source code
├── notebooks/              # Jupyter notebooks
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## 🧠 QCBM Architecture

The Quantum Circuit Born Machine (QCBM) is implemented with:

- **Variational Quantum Circuits**: Parameterized quantum circuits for data representation
- **LSTM Enhancement**: Classical LSTM networks for temporal pattern recognition
- **Hybrid Training**: Combined quantum-classical optimization
- **Efficient Sampling**: Born machine approach for probabilistic data generation

## 📚 Research Background

This project explores the intersection of:

- Quantum machine learning
- Generative modeling
- Temporal sequence modeling
- Variational quantum algorithms

## 🔬 Features

- ✅ Quantum circuit implementation with Qiskit
- ✅ LSTM integration for sequence modeling
- ✅ Hybrid quantum-classical training
- ✅ Born machine sampling techniques
- ✅ Comprehensive evaluation metrics
- ✅ Cloud development environment
- ✅ Jupyter notebook examples

## 🚀 Getting Started with Research

1. **Deploy cloud environment**: `./deploy-cpu.sh qcbm`
2. **Setup SSH**: `./setup-ssh.sh qcbm`
3. **Connect**: `ssh qcbm-container`
4. **Run notebooks**: Access Jupyter at `http://YOUR_IP:8888`
5. **Experiment**: Modify parameters and observe results

## 📝 Requirements

- Python 3.8+
- Qiskit ≥ 1.0.0
- PyTorch ≥ 2.0.0
- NumPy, Matplotlib, Jupyter
- AWS CLI (for cloud deployment)

## 🌟 Advanced Features

- **GPU Support**: Request AWS GPU quota for accelerated training
- **Distributed Training**: Multi-node quantum circuit simulation
- **Custom Datasets**: Easy integration with your data
- **Model Persistence**: Automatic model saving and loading

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

For questions about:

- **Cloud deployment**: Check `.infra/README.md`
- **Research methods**: Open an issue
- **Technical problems**: Contact the maintainers
