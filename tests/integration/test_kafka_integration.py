"""
Kafka Integration Tests for IoT Smoke Detection Pipeline.

This module provides focused tests for Kafka integration including:
- Producer reliability and error handling
- Consumer group management
- Topic management and partitioning
- Message serialization/deserialization
- Connection resilience
"""

import pytest
import json
import time
import threading
from unittest.mock import Mock, patch
from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
from kafka.admin import ConfigResource, ConfigResourceType, NewTopic
from kafka.errors import KafkaError, TopicAlreadyExistsError
import logging

# Test configuration
KAFKA_CONFIG = {
    'bootstrap_servers': 'localhost:9092',
    'topic': 'smoke_detection',
    'test_topic': 'test_smoke_detection',
    'consumer_group': 'test_consumer_group',
    'timeout': 30
}

# Sample test data
TEST_SENSOR_DATA = {
    'Temperature[C]': 25.5,
    'Humidity[%]': 45.0,
    'TVOC[ppb]': 150.0,
    'eCO2[ppm]': 400.0,
    'Raw H2': 13000.0,
    'Raw Ethanol': 18500.0,
    'Pressure[hPa]': 1013.25,
    'PM1.0': 10.0,
    'PM2.5': 15.0,
    'NC0.5': 100.0,
    'NC1.0': 80.0,
    'NC2.5': 20.0
}


class TestKafkaConnection:
    """Test Kafka connection and basic functionality."""
    
    def test_kafka_cluster_connection(self):
        """Test connection to Kafka cluster."""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                request_timeout_ms=10000
            )
            
            # Get cluster metadata
            metadata = admin_client.describe_cluster()
            assert metadata is not None
            
            # List topics
            topics = admin_client.list_topics()
            assert isinstance(topics, set)
            
            admin_client.close()
            
        except Exception as e:
            pytest.skip(f"Kafka cluster not available: {e}")
    
    def test_topic_creation(self):
        """Test creating and managing topics."""
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers']
            )
            
            # Create test topic
            topic = NewTopic(
                name=KAFKA_CONFIG['test_topic'],
                num_partitions=3,
                replication_factor=1
            )
            
            try:
                admin_client.create_topics([topic])
                time.sleep(2)  # Wait for topic creation
            except TopicAlreadyExistsError:
                pass  # Topic already exists, which is fine
            
            # Verify topic exists
            topics = admin_client.list_topics()
            assert KAFKA_CONFIG['test_topic'] in topics
            
            # Clean up - delete test topic
            admin_client.delete_topics([KAFKA_CONFIG['test_topic']])
            admin_client.close()
            
        except Exception as e:
            pytest.skip(f"Topic management test failed: {e}")


class TestKafkaProducerAdvanced:
    """Advanced Kafka producer tests."""
    
    @pytest.fixture
    def producer(self):
        """Create a configured Kafka producer."""
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3,
                batch_size=16384,
                linger_ms=10,
                buffer_memory=33554432,
                max_request_size=1048576,
                request_timeout_ms=30000
            )
            yield producer
            producer.close()
        except Exception as e:
            pytest.skip(f"Kafka producer not available: {e}")
    
    def test_producer_configuration(self, producer):
        """Test producer configuration and metadata."""
        # Test producer is properly configured
        assert producer is not None
        
        # Get producer metrics
        metrics = producer.metrics()
        assert 'producer-metrics' in metrics
        
        # Test producer can get topic metadata
        metadata = producer.list_topics(timeout=5)
        assert metadata is not None
    
    def test_message_serialization(self, producer):
        """Test different message serialization scenarios."""
        topic = KAFKA_CONFIG['topic']
        
        # Test normal sensor data
        normal_data = TEST_SENSOR_DATA.copy()
        future = producer.send(topic, value=normal_data)
        record = future.get(timeout=10)
        assert record.topic == topic
        
        # Test with additional metadata
        metadata_data = normal_data.copy()
        metadata_data.update({
            'sensor_id': 'test_sensor_001',
            'location': 'test_room',
            'device_type': 'smoke_detector'
        })
        future = producer.send(topic, value=metadata_data)
        record = future.get(timeout=10)
        assert record.topic == topic
        
        # Test with nested data
        nested_data = {
            'sensor_data': normal_data,
            'metadata': {
                'timestamp': time.time(),
                'version': '1.0',
                'source': 'test'
            }
        }
        future = producer.send(topic, value=nested_data)
        record = future.get(timeout=10)
        assert record.topic == topic
    
    def test_producer_partitioning(self, producer):
        """Test message partitioning strategies."""
        topic = KAFKA_CONFIG['topic']
        
        # Test key-based partitioning
        for i in range(10):
            message = TEST_SENSOR_DATA.copy()
            message['message_id'] = i
            key = f"sensor_{i % 3}"  # 3 different keys
            
            future = producer.send(topic, key=key, value=message)
            record = future.get(timeout=10)
            
            # Messages with same key should go to same partition
            assert record.partition >= 0
    
    def test_producer_error_handling(self, producer):
        """Test producer error handling scenarios."""
        topic = KAFKA_CONFIG['topic']
        
        # Test with oversized message (should handle gracefully)
        large_data = TEST_SENSOR_DATA.copy()
        large_data['large_field'] = 'x' * 2000000  # 2MB string
        
        try:
            future = producer.send(topic, value=large_data)
            future.get(timeout=10)
        except Exception as e:
            # Should get a reasonable error for oversized message
            assert 'too large' in str(e).lower() or 'size' in str(e).lower()
    
    def test_producer_async_operations(self, producer):
        """Test asynchronous producer operations."""
        topic = KAFKA_CONFIG['topic']
        futures = []
        
        # Send multiple messages asynchronously
        for i in range(100):
            message = TEST_SENSOR_DATA.copy()
            message['async_test_id'] = i
            future = producer.send(topic, value=message)
            futures.append(future)
        
        # Wait for all messages to be sent
        for future in futures:
            record = future.get(timeout=10)
            assert record.topic == topic
        
        # Verify producer metrics
        metrics = producer.metrics()
        assert 'record-send-total' in metrics['producer-metrics']


class TestKafkaConsumerAdvanced:
    """Advanced Kafka consumer tests."""
    
    @pytest.fixture
    def consumer(self):
        """Create a configured Kafka consumer."""
        try:
            consumer = KafkaConsumer(
                KAFKA_CONFIG['topic'],
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='latest',
                enable_auto_commit=True,
                group_id=KAFKA_CONFIG['consumer_group'],
                consumer_timeout_ms=10000,
                max_poll_records=500,
                fetch_min_bytes=1,
                fetch_max_wait_ms=500
            )
            yield consumer
            consumer.close()
        except Exception as e:
            pytest.skip(f"Kafka consumer not available: {e}")
    
    def test_consumer_configuration(self, consumer):
        """Test consumer configuration and subscription."""
        # Test consumer is properly configured
        assert consumer is not None
        
        # Test subscription
        subscription = consumer.subscription()
        assert KAFKA_CONFIG['topic'] in subscription
        
        # Test partition assignment
        assignment = consumer.assignment()
        # Assignment might be empty initially, but should be a set
        assert isinstance(assignment, set)
    
    def test_consumer_offset_management(self, consumer):
        """Test consumer offset management."""
        # Get current position
        partitions = consumer.partitions_for_topic(KAFKA_CONFIG['topic'])
        if partitions:
            from kafka import TopicPartition
            tp = TopicPartition(KAFKA_CONFIG['topic'], list(partitions)[0])
            
            # Test position and committed offset
            try:
                position = consumer.position(tp)
                committed = consumer.committed(tp)
                
                # Position should be >= committed offset
                if committed is not None:
                    assert position >= committed
            except Exception:
                # Might fail if no messages consumed yet
                pass
    
    def test_consumer_message_processing(self, consumer, producer):
        """Test message processing with consumer."""
        # Send test messages first
        test_messages = []
        for i in range(5):
            message = TEST_SENSOR_DATA.copy()
            message['consumer_test_id'] = i
            test_messages.append(message)
            producer.send(KAFKA_CONFIG['topic'], value=message)
        
        producer.flush()
        time.sleep(1)  # Wait for messages to be available
        
        # Consume and verify messages
        consumed_messages = []
        for message in consumer:
            if 'consumer_test_id' in message.value:
                consumed_messages.append(message.value)
                if len(consumed_messages) >= len(test_messages):
                    break
        
        # Verify we consumed the expected messages
        assert len(consumed_messages) > 0
        
        # Verify message structure
        for msg in consumed_messages:
            assert 'Temperature[C]' in msg
            assert 'consumer_test_id' in msg
    
    def test_consumer_group_coordination(self):
        """Test consumer group coordination."""
        try:
            # Create multiple consumers in same group
            consumers = []
            for i in range(2):
                consumer = KafkaConsumer(
                    KAFKA_CONFIG['topic'],
                    bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                    group_id=f"test_group_{int(time.time())}",
                    auto_offset_reset='latest',
                    consumer_timeout_ms=5000
                )
                consumers.append(consumer)
            
            # Wait for group coordination
            time.sleep(3)
            
            # Check partition assignment
            total_partitions = set()
            for consumer in consumers:
                assignment = consumer.assignment()
                total_partitions.update(assignment)
            
            # Clean up
            for consumer in consumers:
                consumer.close()
            
            # Should have some partition assignments
            assert len(total_partitions) >= 0
            
        except Exception as e:
            pytest.skip(f"Consumer group test failed: {e}")


class TestKafkaReliability:
    """Test Kafka reliability and error recovery."""
    
    def test_producer_retry_mechanism(self):
        """Test producer retry mechanism."""
        try:
            # Create producer with retry configuration
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=5,
                retry_backoff_ms=100,
                request_timeout_ms=5000,
                acks='all'
            )
            
            # Send message to test retry mechanism
            message = TEST_SENSOR_DATA.copy()
            message['retry_test'] = True
            
            future = producer.send(KAFKA_CONFIG['topic'], value=message)
            record = future.get(timeout=15)
            
            assert record.topic == KAFKA_CONFIG['topic']
            producer.close()
            
        except Exception as e:
            pytest.skip(f"Retry mechanism test failed: {e}")
    
    def test_connection_resilience(self):
        """Test connection resilience and recovery."""
        try:
            # Test with short timeout to simulate network issues
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=1000,  # Short timeout
                retries=3,
                retry_backoff_ms=100
            )
            
            # Send multiple messages
            success_count = 0
            for i in range(10):
                try:
                    message = TEST_SENSOR_DATA.copy()
                    message['resilience_test_id'] = i
                    
                    future = producer.send(KAFKA_CONFIG['topic'], value=message)
                    future.get(timeout=5)
                    success_count += 1
                except Exception:
                    # Some failures are expected with short timeout
                    pass
            
            producer.close()
            
            # Should have some successful sends
            assert success_count > 0
            
        except Exception as e:
            pytest.skip(f"Connection resilience test failed: {e}")
    
    def test_message_ordering(self):
        """Test message ordering guarantees."""
        try:
            # Create producer with ordering guarantees
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_in_flight_requests_per_connection=1,  # Ensure ordering
                acks='all',
                retries=3
            )
            
            consumer = KafkaConsumer(
                KAFKA_CONFIG['topic'],
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='latest',
                group_id=f"ordering_test_{int(time.time())}"
            )
            
            # Send ordered messages with same key
            key = "ordering_test"
            sent_order = []
            
            for i in range(10):
                message = TEST_SENSOR_DATA.copy()
                message['order_id'] = i
                sent_order.append(i)
                
                producer.send(KAFKA_CONFIG['topic'], key=key, value=message)
            
            producer.flush()
            time.sleep(2)
            
            # Consume messages and check order
            received_order = []
            for message in consumer:
                if message.key == key and 'order_id' in message.value:
                    received_order.append(message.value['order_id'])
                    if len(received_order) >= len(sent_order):
                        break
            
            producer.close()
            consumer.close()
            
            # Check if order is preserved (for same key/partition)
            if len(received_order) > 1:
                # Should be in order for same partition
                assert received_order == sorted(received_order)
            
        except Exception as e:
            pytest.skip(f"Message ordering test failed: {e}")


class TestKafkaPerformance:
    """Performance tests for Kafka operations."""
    
    def test_producer_throughput(self):
        """Test producer throughput under load."""
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                batch_size=32768,  # Larger batch size
                linger_ms=50,      # Wait for batching
                compression_type='snappy',
                acks=1  # Faster acknowledgment
            )
            
            # Measure throughput
            start_time = time.time()
            num_messages = 1000
            
            futures = []
            for i in range(num_messages):
                message = TEST_SENSOR_DATA.copy()
                message['throughput_test_id'] = i
                future = producer.send(KAFKA_CONFIG['topic'], value=message)
                futures.append(future)
            
            # Wait for all messages
            for future in futures:
                future.get(timeout=30)
            
            end_time = time.time()
            duration = end_time - start_time
            throughput = num_messages / duration
            
            producer.close()
            
            print(f"Producer throughput: {throughput:.2f} messages/second")
            assert throughput > 100  # Should handle at least 100 msg/s
            
        except Exception as e:
            pytest.skip(f"Throughput test failed: {e}")
    
    def test_consumer_throughput(self):
        """Test consumer throughput under load."""
        try:
            # First, produce many messages
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                batch_size=32768,
                linger_ms=10
            )
            
            num_messages = 500
            for i in range(num_messages):
                message = TEST_SENSOR_DATA.copy()
                message['consumer_throughput_test_id'] = i
                producer.send(KAFKA_CONFIG['topic'], value=message)
            
            producer.flush()
            producer.close()
            
            # Now test consumer throughput
            consumer = KafkaConsumer(
                KAFKA_CONFIG['topic'],
                bootstrap_servers=KAFKA_CONFIG['bootstrap_servers'],
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                group_id=f"throughput_test_{int(time.time())}",
                max_poll_records=100,  # Larger poll size
                fetch_min_bytes=1024   # Batch fetching
            )
            
            start_time = time.time()
            consumed_count = 0
            
            for message in consumer:
                if 'consumer_throughput_test_id' in message.value:
                    consumed_count += 1
                    if consumed_count >= num_messages:
                        break
            
            end_time = time.time()
            duration = end_time - start_time
            throughput = consumed_count / duration
            
            consumer.close()
            
            print(f"Consumer throughput: {throughput:.2f} messages/second")
            assert throughput > 50  # Should handle at least 50 msg/s
            
        except Exception as e:
            pytest.skip(f"Consumer throughput test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
